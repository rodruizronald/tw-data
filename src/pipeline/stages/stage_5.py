"""
Stage 5: Upload jobs to Supabase.

This stage takes jobs that have completed stages 1-4 and uploads them
to Supabase for storage. If a job already exists (same signature),
it will be updated instead of created. Additionally, it associates
technologies with jobs and tracks unmatched technologies.
"""

import time

from prefect.logging import get_run_logger

from core.models.jobs import Job
from core.models.metrics import StageMetricsInput, StageStatus
from data.mongo import unmatched_technology_repository
from data.supebase.exceptions import (
    SupabaseAuthError,
    SupabaseConflictError,
    SupabaseConnectionError,
    SupabaseNotFoundError,
    SupabaseRateLimitError,
    SupabaseServerError,
    SupabaseValidationError,
)
from data.supebase.models.job import Job as SupabaseJob
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

        # Initialize repositories
        self.unmatched_tech_repo = unmatched_technology_repository

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
        """Upload a batch of jobs to Supabase and associate technologies."""
        processed_jobs: list[Job] = []
        failed_count = 0

        for job in jobs:
            try:
                # Upload job to Supabase
                supabase_job = self._upload_job_to_supabase(job, company_id)
                self.logger.info(f"Job '{job.title}' successfully uploaded to Supabase")

                # Associate technologies with the job
                tech_success = self._associate_job_technologies(job, supabase_job.id)

                if tech_success:
                    processed_jobs.append(job)
                    self.logger.info(
                        f"Job '{job.title}' technologies associated successfully"
                    )
                else:
                    failed_count += 1
                    self.logger.warning(
                        f"Job '{job.title}' uploaded but technology association failed"
                    )

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

        self.logger.info(f"Failed to process {failed_count} jobs")
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

    def _upload_job_to_supabase(self, job: Job, company_id: int) -> SupabaseJob:
        """
        Upload a single job to Supabase (create or update).

        Args:
            job: Job object to upload
            company_id: Supabase company ID

        Returns:
            SupabaseJob: The created or updated Supabase job

        Raises:
            Exception: If upload fails
        """
        # Check if job already exists in Supabase
        if self.supabase_service.job_exists(job.signature):
            # Update existing job
            return self.supabase_service.update_job(job, company_id)
        else:
            # Create new job
            return self.supabase_service.create_job(job, company_id)

    def _associate_job_technologies(self, job: Job, job_id: int) -> bool:
        """
        Associate technologies from the job posting with the Supabase job.

        For each technology mentioned in the job posting:
        1. Search for the technology in the database by exact name
        2. If not found by name, search using technology aliases
        3. Create a link between the job and the technology
        4. If a technology cannot be found at all, store it in unmatched_technologies

        Args:
            job: Job object containing technologies
            job_id: Supabase job ID

        Returns:
            bool: True if all technologies were successfully processed, False otherwise
        """
        # Check if job has technologies
        if job.technologies is None or not job.technologies.technologies:
            self.logger.debug(f"Job '{job.title}' has no technologies to associate")
            return True

        all_succeeded = True

        for tech in job.technologies.technologies:
            tech_name = tech.name

            try:
                # Try to resolve the technology ID
                technology_id = self._resolve_technology_id(tech_name)

                if technology_id is not None:
                    # Create the job-technology association
                    self.supabase_service.create_job_technology(job_id, technology_id)
                    self.logger.debug(
                        f"Associated technology '{tech_name}' with job '{job.title}'"
                    )
                else:
                    # Technology not found - store as unmatched
                    self.unmatched_tech_repo.create_if_not_exists(tech_name)
                    self.logger.warning(
                        f"Technology '{tech_name}' not found, stored as unmatched"
                    )

            except SupabaseConflictError:
                # Job-technology association already exists - this is OK
                self.logger.debug(
                    f"Technology '{tech_name}' already associated with job '{job.title}'"
                )

            except (
                SupabaseAuthError,
                SupabaseConnectionError,
                SupabaseServerError,
                SupabaseRateLimitError,
            ):
                # Critical errors - bubble up
                raise

            except Exception as e:
                # Log error and mark as failed, but continue with other technologies
                self.logger.error(
                    f"Failed to associate technology '{tech_name}' with job "
                    f"'{job.title}': {e}"
                )
                all_succeeded = False

        return all_succeeded

    def _resolve_technology_id(self, tech_name: str) -> int | None:
        """
        Resolve a technology name to its Supabase ID.

        First tries to find by exact name, then by alias.

        Args:
            tech_name: Technology name to resolve

        Returns:
            int: Technology ID if found, None otherwise
        """
        # Try to find by exact name
        try:
            technology = self.supabase_service.get_technology_by_name(tech_name)
            technology_id: int = technology.id
            return technology_id
        except SupabaseNotFoundError:
            pass

        # Try to find by alias
        try:
            alias = self.supabase_service.get_technology_alias_by_name(tech_name)
            alias_technology_id: int = alias.technology_id
            return alias_technology_id
        except SupabaseNotFoundError:
            pass

        # Technology not found
        return None
