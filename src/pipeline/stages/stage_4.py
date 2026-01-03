import json
import time

from prefect.logging import get_run_logger

from core.config.services import WebParserConfig
from core.mappers.jobs import JobTechnologiesMapper
from core.models.jobs import Job, JobTechnologies
from core.models.metrics import StageMetricsInput, StageStatus
from pipeline.config import PipelineConfig
from services.data_service import JobDataService
from services.metrics_service import JobMetricsService
from services.openai_service import OpenAIRequest, OpenAIService
from services.web_extraction_service import WebExtractionService
from utils.exceptions import (
    DatabaseOperationError,
    OpenAIProcessingError,
)
from utils.timezone import now_utc


class Stage4Processor:
    """Stage 4: Extract technologies and tools from job postings."""

    def __init__(self, config: PipelineConfig, web_parser: WebParserConfig):
        """Initialize Stage 4 processor with required services."""
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
        self.job_technologies_mapper = JobTechnologiesMapper()

    async def process_jobs(self, jobs: list[Job], company_name: str) -> list[Job]:
        """
        Process multiple jobs for a company to extract technologies and tools.

        Args:
            jobs: List of Job objects to enrich with Stage 4 data
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
                        processed_jobs, company_name, self.config.stage_4.tag
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
                        stage=self.config.stage_4.tag,
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
            # Record stage metrics
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
                stage=self.config.stage_4.tag,
                metrics_input=metrics_input,
            )

    async def process_single_job(self, job: Job) -> Job:
        """
        Process a single job to extract technologies and tools.

        Args:
            job: Job instance to enrich with Stage 4 data

        Returns:
            Job: Enriched job with Stage 4 technologies data

        Raises:
            WebExtractionError: If HTML extraction fails
            OpenAIProcessingError: If AI processing fails
            ValueError: If job technologies mapping fails
        """
        self.logger.info(f"Processing job: {job.title}")

        # Step 1: Use OpenAI service to parse job technologies
        job_technologies = await self._parse_job_technologies(job)

        # Step 2: Enrich job with technologies
        job.technologies = job_technologies

        return job

    async def _parse_job_technologies(self, job: Job) -> JobTechnologies:
        """Parse job technologies from HTML content using the OpenAI service."""
        try:
            # Check if job has requirements from Stage 3
            if not job.requirements:
                raise ValueError(
                    f"Job {job.title} has no requirements data from Stage 3"
                )

            prompt_template = self.config.stage_4.prompt_template
            job_requirements = {
                "must_have": job.requirements.skill_must_have,
                "nice_to_have": job.requirements.skill_nice_to_have,
            }
            # Convert requirements to JSON string for the prompt
            requirements_json = json.dumps({"requirements": job_requirements}, indent=2)

            request = OpenAIRequest(
                system_message=self.config.stage_4.system_message,
                template_path=self.config.get_prompt_path(prompt_template),
                template_variables={
                    "requirements_json": requirements_json,
                },
                response_format=self.config.stage_4.response_format,
                context_name=job.company,
            )

            # Get raw response from OpenAI
            raw_response = await self.openai_service.process_with_template(request)

            # Process and validate job data using JobTechnologiesMapper
            job_technologies = self.job_technologies_mapper.map_from_openai_response(
                raw_response
            )

            return job_technologies

        except OpenAIProcessingError:
            # Already properly typed - just re-raise without wrapping
            raise
        except Exception as e:
            # Only wrap unexpected exceptions
            raise OpenAIProcessingError(
                message=f"Failed to parse job technologies for {job.title}: {e}",
                company_name=job.company,
            ) from e
