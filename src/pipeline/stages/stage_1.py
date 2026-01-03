import time

from prefect.logging import get_run_logger

from core.mappers.jobs import JobMapper
from core.models.jobs import CompanyData, Job
from core.models.metrics import StageMetricsInput, StageStatus
from pipeline.config import PipelineConfig
from services.data_service import JobDataService
from services.metrics_service import JobMetricsService
from services.openai_service import OpenAIRequest, OpenAIService
from services.supabase_service import SupabaseService
from services.web_extraction_service import WebExtractionService
from utils.exceptions import (
    CompanyProcessingError,
    DatabaseOperationError,
    OpenAIProcessingError,
    ValidationError,
    WebExtractionError,
)
from utils.timezone import now_utc


class Stage1Processor:
    """Stage 1: Extract job listings from company career pages."""

    def __init__(self, config: PipelineConfig):
        """
        Initialize Stage 1 processor.

        Args:
            config: Pipeline configuration
            prompt_template_path: Path to the OpenAI prompt template
        """
        logger = get_run_logger()

        self.config = config
        self.logger = logger

        # Initialize services
        self.openai_service = OpenAIService(config.openai)
        self.database_service = JobDataService()
        self.metrics_service = JobMetricsService()
        self.web_extraction_service = WebExtractionService(config.web_extraction)
        self.supabase_service = SupabaseService()
        # Initialize mapper
        self.job_mapper = JobMapper()

    async def process_single_company(self, company: CompanyData) -> list[Job]:
        """
        Process a single company to extract job listings.

        This method is designed to be called by Prefect tasks and handles
        one company at a time with comprehensive error handling and timing.

        Args:
            company: Company information and configuration

        """
        company_name = company.name
        start_time = time.time()
        started_at = now_utc()
        jobs_processed = 0
        jobs_completed = 0
        status = StageStatus.FAILED
        error_message = None

        try:
            # Process the company
            new_jobs = await self._execute_company_processing(company)

            jobs_processed = len(new_jobs)
            jobs_completed = len(new_jobs)
            status = StageStatus.SUCCESS

            return new_jobs

        except ValidationError as e:
            # Non-retryable error - bad company data
            self.logger.error(f"Validation failed - {e}")
            error_message = str(e)
            status = StageStatus.FAILED
            return []  # Return empty list instead of None

        except (WebExtractionError, OpenAIProcessingError) as e:
            # Potentially retryable errors - network/API issues
            self.logger.error(f"{type(e).__name__} - {e}")
            error_message = str(e)
            status = StageStatus.FAILED
            # Re-raise these for Prefect retry mechanism
            raise

        except DatabaseOperationError as e:
            # Database errors - usually retryable
            self.logger.error(f"Database operation failed - {e}")
            error_message = str(e)
            status = StageStatus.FAILED
            # Re-raise these for Prefect retry mechanism
            raise

        except Exception as e:
            # Unexpected errors
            self.logger.error(f"Unexpected error - {e}")
            error_message = str(e)
            status = StageStatus.FAILED

            # Still raise CompanyProcessingError for upstream handling if needed
            raise CompanyProcessingError(
                company_name, e, self.config.stage_1.tag
            ) from e

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
                    stage=self.config.stage_1.tag,
                    metrics_input=metrics_input,
                )
            except Exception as metrics_error:
                self.logger.warning(
                    f"Failed to record stage metrics for {company_name}: {metrics_error}"
                )

    async def _execute_company_processing(self, company: CompanyData) -> list[Job]:
        """Execute the main processing logic for a company."""
        # Extract HTML content from career page
        html_content = await self._extract_career_page_content(company)

        # Parse job listings using OpenAI
        found_jobs = await self._parse_job_listings(company, html_content)
        self.logger.info(f"Job data processed: {len(found_jobs)} jobs found")

        # Deactivate jobs that are no longer on the career page
        self._deactivate_missing_jobs(company, found_jobs)

        # Filter out existing jobs
        new_jobs = self._filter_existing_jobs(company, found_jobs)

        # Save jobs to database
        if new_jobs:
            try:
                saved_count = self.database_service.save_stage_results(
                    new_jobs, company.name, self.config.stage_1.tag
                )
                self.logger.info(f"Saved {saved_count} new jobs to database")
            except Exception as e:
                raise DatabaseOperationError(
                    operation="save_stage_results",
                    message=str(e),
                    company_name=company.name,
                    stage=self.config.stage_1.tag,
                ) from e

        return new_jobs

    async def _extract_career_page_content(self, company: CompanyData) -> str:
        """Extract HTML content from company career page."""
        try:
            content = await self.web_extraction_service.extract_html_content(
                url=company.career_url,
                selectors=company.job_board_selectors,
                parser_type=company.parser_type,
                company_name=company.name,
            )
            if not content:
                raise WebExtractionError(
                    url=company.career_url,
                    original_error=Exception(
                        f"No content extracted from {company.career_url}"
                    ),
                    company_name=company.name,
                )
            html_content: str = content
            return html_content
        except WebExtractionError:
            # Already properly typed - just re-raise without wrapping
            raise
        except Exception as e:
            # Only wrap unexpected exceptions
            raise WebExtractionError(
                url=company.career_url,
                original_error=e,
                company_name=company.name,
            ) from e

    async def _parse_job_listings(
        self, company: CompanyData, html_content: str
    ) -> list[Job]:
        """Parse job listings from HTML content using the job extraction service."""
        try:
            prompt_template = self.config.stage_1.prompt_template
            request = OpenAIRequest(
                system_message=self.config.stage_1.system_message,
                template_path=self.config.get_prompt_path(prompt_template),
                template_variables={
                    "html_content": html_content,
                    "career_url": company.career_url,
                },
                response_format=self.config.stage_1.response_format,
                context_name=company.name,
            )

            # Get raw response from OpenAI
            job_listings = await self.openai_service.process_with_template(request)

            # Process and validate job data using JobMapper
            jobs: list[Job] = self.job_mapper.map_from_openai_response(
                job_listings, company.name
            )

            return jobs
        except OpenAIProcessingError:
            # Already properly typed - just re-raise without wrapping
            raise
        except Exception as e:
            # Only wrap unexpected exceptions
            raise OpenAIProcessingError(
                message=f"Failed to parse job listings: {e}",
                company_name=company.name,
            ) from e

    def _filter_existing_jobs(self, company: CompanyData, jobs: list[Job]) -> list[Job]:
        """Filter out existing jobs and return only new ones."""
        if not jobs:
            return jobs

        try:
            # Load existing signatures from database
            existing_job_signatures = self.database_service.get_existing_signatures(
                company.name
            )
        except Exception as e:
            raise DatabaseOperationError(
                operation="get_existing_signatures",
                message=str(e),
                company_name=company.name,
                stage=self.config.stage_1.tag,
            ) from e

        # Filter out existing jobs
        current_signatures = {job.signature for job in jobs}
        duplicate_signatures = current_signatures.intersection(existing_job_signatures)
        new_jobs = [job for job in jobs if job.signature not in duplicate_signatures]

        if duplicate_signatures:
            self.logger.info(
                f"Filtered out {len(duplicate_signatures)} existing jobs. "
                f"Found {len(new_jobs)} new jobs."
            )

        return new_jobs

    def _deactivate_missing_jobs(self, company: CompanyData, jobs: list[Job]) -> None:
        """Deactivate jobs that are no longer on the career page."""
        current_signatures = {job.signature for job in jobs}
        try:
            deactivated_signatures = self.database_service.deactivate_missing_jobs(
                company.name, current_signatures
            )
            if deactivated_signatures:
                # Deactivate jobs in Supabase by signature
                for signature in deactivated_signatures:
                    try:
                        self.supabase_service.deactivate_job(signature)
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to deactivate job in Supabase: {signature[:20]}... - {e}"
                        )
                self.logger.info(
                    f"Deactivated {len(deactivated_signatures)} jobs no longer on career page"
                )
        except Exception as e:
            raise DatabaseOperationError(
                operation="deactivate_missing_jobs",
                message=str(e),
                company_name=company.name,
                stage=self.config.stage_1.tag,
            ) from e
