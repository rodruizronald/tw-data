import time

from prefect.logging import get_run_logger

from core.config.services import WebParserConfig
from core.mappers.jobs import JobRequirementsMapper
from core.models.jobs import Job, JobRequirements
from core.models.metrics import StageMetricsInput, StageStatus
from pipeline.config import PipelineConfig
from services.data_service import JobDataService
from services.metrics_service import JobMetricsService
from services.openai_service import OpenAIRequest, OpenAIService
from services.web_extraction_service import WebExtractionService
from utils.exceptions import (
    DatabaseOperationError,
    OpenAIProcessingError,
    WebExtractionError,
)
from utils.timezone import now_utc


class Stage3Processor:
    """Stage 3: Extract skills and responsibilities from job postings."""

    def __init__(self, config: PipelineConfig, web_parser: WebParserConfig):
        """Initialize Stage 3 processor with required services."""
        logger = get_run_logger()

        self.config = config
        self.logger = logger
        self.web_parser = web_parser

        # Initialize services
        self.openai_service = OpenAIService(config.openai)
        self.database_service = JobDataService()
        self.metrics_service = JobMetricsService()
        self.web_extraction_service = WebExtractionService(config.web_extraction)

        # Initialize mapper
        self.job_requirments_mapper = JobRequirementsMapper()

    async def process_jobs(self, jobs: list[Job], company_name: str) -> list[Job]:
        """
        Process multiple jobs for a company to extract skills and responsibilities.

        Args:
            jobs: List of Job objects to enrich with Stage 3 data
            company_name: Name of the company

        """
        self.logger.info(f"Processing {len(jobs)} jobs for {company_name}")

        start_time = time.time()
        started_at = now_utc()
        jobs_processed = len(jobs)
        jobs_completed = 0
        status = StageStatus.FAILED
        error_message = None

        try:
            processed_jobs = []
            failed_jobs = []

            for job in jobs:
                try:
                    # Process and enrich the job
                    enriched_job = await self.process_single_job(job)
                    processed_jobs.append(enriched_job)
                    self.logger.info(
                        f"Job {job.title} successfully processed and added to results"
                    )

                except Exception as e:
                    failed_jobs.append((job, e))
                    self.logger.error(f"Failed to process {job.title}: {e}")

            jobs_completed = len(processed_jobs)

            # Save all processed jobs to database
            if processed_jobs:
                try:
                    saved_count = self.database_service.save_stage_results(
                        processed_jobs, company_name, self.config.stage_3.tag
                    )
                    self.logger.info(
                        f"Saved {saved_count} processed jobs for {company_name}. "
                        f"Failed to process {len(failed_jobs)} jobs."
                    )
                    status = StageStatus.SUCCESS
                except Exception as e:
                    error_message = str(e)
                    status = StageStatus.FAILED
                    raise DatabaseOperationError(
                        operation="save_stage_results",
                        message=str(e),
                        company_name=company_name,
                        stage=self.config.stage_3.tag,
                    ) from e
            else:
                self.logger.warning(f"No jobs to save for {company_name}")
                status = StageStatus.FAILED
                error_message = "No jobs successfully processed"

            return processed_jobs

        except DatabaseOperationError:
            # Re-raise database errors for retry mechanism
            raise

        except Exception as e:
            self.logger.error(f"Error processing jobs for {company_name}: {e!s}")
            error_message = str(e)
            status = StageStatus.FAILED
            return []  # Return empty list instead of None

        finally:
            # Record stage metrics - protected to avoid masking original errors
            try:
                execution_time = time.time() - start_time
                completed_at = now_utc()

                metrics_input = StageMetricsInput(
                    status=status,
                    jobs_processed=jobs_processed,
                    jobs_completed=jobs_completed,
                    jobs_failed=jobs_processed - jobs_completed,
                    execution_seconds=execution_time,
                    started_at=started_at,
                    completed_at=completed_at,
                    error_message=error_message,
                )

                self.metrics_service.record_stage_metrics(
                    company_name=company_name,
                    stage=self.config.stage_3.tag,
                    metrics_input=metrics_input,
                )
            except Exception as metrics_error:
                self.logger.warning(
                    f"Failed to record stage metrics for {company_name}: {metrics_error}"
                )

    async def process_single_job(self, job: Job) -> Job:
        """
        Process a single job to extract skills and responsibilities.

        Args:
            job: Job instance to enrich with Stage 3 data

        Returns:
            Job: Enriched job with Stage 3 skills data

        Raises:
            WebExtractionError: If HTML extraction fails
            OpenAIProcessingError: If AI processing fails
            ValueError: If job skills mapping fails
        """
        self.logger.info(f"Processing job: {job.title}")

        # Step 1: Extract job posting page content
        html_content = await self._extract_job_skills_content(job)

        # Step 2: Use OpenAI service to parse job skills
        job_requirements = await self._parse_job_skills(html_content, job)

        # Step 3: Enrich job with skills
        job.requirements = job_requirements

        return job

    async def _extract_job_skills_content(self, job: Job) -> str:
        """Extract HTML content from job posting page."""
        try:
            content = await self.web_extraction_service.extract_html_content(
                url=job.url,
                selectors=self.web_parser.job_card_selectors,
                parser_type=self.web_parser.job_card_parser_type,
                company_name=job.company,
            )
            if not content:
                raise WebExtractionError(
                    url=job.url,
                    original_error=Exception(f"No content extracted from {job.url}"),
                    company_name=job.company,
                )
            html_content: str = content
            return html_content
        except WebExtractionError:
            # Already properly typed - just re-raise without wrapping
            raise
        except Exception as e:
            # Only wrap unexpected exceptions
            raise WebExtractionError(
                url=job.url,
                original_error=e,
                company_name=job.company,
            ) from e

    async def _parse_job_skills(self, html_content: str, job: Job) -> JobRequirements:
        """Parse job skills from HTML content using the OpenAI service."""
        try:
            prompt_template = self.config.stage_3.prompt_template
            request = OpenAIRequest(
                system_message=self.config.stage_3.system_message,
                template_path=self.config.get_prompt_path(prompt_template),
                template_variables={
                    "html_content": html_content,
                },
                response_format=self.config.stage_3.response_format,
                context_name=job.company,
            )

            # Get raw response from OpenAI
            raw_response = await self.openai_service.process_with_template(request)

            # Process and validate job data using JobRequirementsMapper
            job_requirements = self.job_requirments_mapper.map_from_openai_response(
                raw_response
            )

            return job_requirements

        except OpenAIProcessingError:
            # Already properly typed - just re-raise without wrapping
            raise
        except Exception as e:
            # Only wrap unexpected exceptions
            raise OpenAIProcessingError(
                message=f"Failed to parse job skills for {job.title}: {e}",
                company_name=job.company,
            ) from e
