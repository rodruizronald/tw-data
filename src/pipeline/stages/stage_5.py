"""
Stage 5: Upload jobs to Supabase.

This stage takes jobs that have completed stages 1-4 and uploads them
to Supabase for storage. If a job already exists (same signature),
it will be updated instead of created.
"""

import time

from prefect.logging import get_run_logger

from core.models.jobs import Job
from core.models.metrics import StageMetricsInput, StageStatus
from data.supebase.exceptions import (
    SupabaseAuthError,
    SupabaseConflictError,
    SupabaseConnectionError,
    SupabaseNotFoundError,
    SupabaseRateLimitError,
    SupabaseServerError,
    SupabaseValidationError,
)
from pipeline.config import PipelineConfig
from services.data_service import JobDataService
from services.metrics_service import JobMetricsService
from services.supabase_service import SupabaseService
from utils.exceptions import DatabaseOperationError
from utils.timezone import now_utc


class Stage5Processor:
    """Stage 5: Upload jobs to Supabase database."""

    def __init__(self, config: PipelineConfig):
        """Initialize Stage 5 processor with required services."""
        logger = get_run_logger()

        self.config = config
        self.logger = logger

        # Initialize services
        self.supabase_service = SupabaseService()
        self.database_service = JobDataService()
        self.metrics_service = JobMetricsService()

    def process_jobs(self, jobs: list[Job], company_name: str) -> list[Job]:
        """
        Process multiple jobs for a company to upload them to Supabase.

        Args:
            jobs: List of Job objects to upload to Supabase
            company_name: Name of the company

        Returns:
            List of successfully processed jobs
        """
        self.logger.info(f"Processing {len(jobs)} jobs for {company_name}")

        start_time = time.time()
        started_at = now_utc()
        jobs_processed = len(jobs)
        jobs_completed = 0
        status = StageStatus.FAILED
        error_message = None

        try:
            # Get company ID from Supabase
            company_id = self._get_company_id(company_name)
            if company_id is None:
                error_message = f"Company '{company_name}' not found in Supabase"
                return []

            # Upload jobs to Supabase
            processed_jobs = self._upload_jobs_batch(jobs, company_id)
            jobs_completed = len(processed_jobs)

            # Save results to MongoDB
            status, error_message = self._save_processed_jobs(
                processed_jobs, company_name
            )

            return processed_jobs

        except DatabaseOperationError:
            raise

        # Critical Supabase errors - bubble up for task-level retry
        except (
            SupabaseAuthError,
            SupabaseConnectionError,
            SupabaseServerError,
            SupabaseRateLimitError,
        ):
            raise

        except Exception as e:
            self.logger.error(f"Error processing jobs for {company_name}: {e!s}")
            error_message = str(e)
            status = StageStatus.FAILED
            return []

        finally:
            self._record_metrics(
                company_name,
                jobs_processed,
                jobs_completed,
                status,
                error_message,
                start_time,
                started_at,
            )

    def _get_company_id(self, company_name: str) -> int | None:
        """Get company ID from Supabase by name."""
        try:
            company = self.supabase_service.get_company_by_name(company_name)
            company_id: int = company.id
            return company_id
        except SupabaseNotFoundError:
            self.logger.error(f"Company '{company_name}' not found in Supabase")
            return None
        except (SupabaseAuthError, SupabaseConnectionError, SupabaseServerError):
            # Critical errors - let them bubble up
            raise

    def _upload_jobs_batch(self, jobs: list[Job], company_id: int) -> list[Job]:
        """Upload a batch of jobs to Supabase."""
        processed_jobs: list[Job] = []
        failed_count = 0

        for job in jobs:
            try:
                self._upload_job_to_supabase(job, company_id)
                processed_jobs.append(job)
                self.logger.info(f"Job '{job.title}' successfully uploaded to Supabase")

            # Per-job recoverable errors - skip and continue
            except (SupabaseValidationError, SupabaseConflictError) as e:
                failed_count += 1
                self.logger.warning(f"Skipping job '{job.title}': {e}")

            # Critical errors - stop batch and bubble up
            except (
                SupabaseAuthError,
                SupabaseConnectionError,
                SupabaseServerError,
                SupabaseRateLimitError,
            ):
                raise

            except Exception as e:
                failed_count += 1
                self.logger.error(f"Failed to upload job '{job.title}': {e}")

        self.logger.info("Failed to upload {failed_count} jobs to supabase")
        return processed_jobs

    def _save_processed_jobs(
        self, processed_jobs: list[Job], company_name: str
    ) -> tuple[StageStatus, str | None]:
        """Mark processed jobs as stage 5 completed in MongoDB."""
        if not processed_jobs:
            self.logger.warning(f"No jobs to save for {company_name}")
            return StageStatus.FAILED, "No jobs successfully uploaded to Supabase"

        try:
            signatures = [job.signature for job in processed_jobs]
            self.database_service.mark_stage_5_completed(signatures)
            return StageStatus.SUCCESS, None
        except Exception as e:
            raise DatabaseOperationError(
                operation="mark_stage_5_completed",
                message=str(e),
                company_name=company_name,
                stage=self.config.stage_5.tag,
            ) from e

    def _record_metrics(
        self,
        company_name: str,
        jobs_processed: int,
        jobs_completed: int,
        status: StageStatus,
        error_message: str | None,
        start_time: float,
        started_at,
    ) -> None:
        """Record stage metrics."""
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
            stage=self.config.stage_5.tag,
            metrics_input=metrics_input,
        )

    def _upload_job_to_supabase(self, job: Job, company_id: int) -> None:
        """
        Upload a single job to Supabase (create or update).

        Args:
            job: Job object to upload
            company_id: Supabase company ID

        Raises:
            Exception: If upload fails
        """
        # Check if job already exists in Supabase
        if self.supabase_service.job_exists(job.signature):
            # Update existing job
            self.supabase_service.update_job(job, company_id)
        else:
            # Create new job
            self.supabase_service.create_job(job, company_id)
