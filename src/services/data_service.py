"""
Service for managing job data operations across pipeline stages.

Provides database-backed persistence for job listings, handling CRUD operations,
stage tracking, deduplication, and statistics for the multi-stage job processing pipeline.
"""

import logging
from typing import Any

from core.models.jobs import Job
from data.mongo import (
    job_listing_repository,
)
from data.mongo.mappers.job_mapper import JobMapper
from utils.timezone import UTC_TZ, now_utc

logger = logging.getLogger(__name__)


class JobDataService:
    """Service for handling job database operations in the pipeline."""

    def __init__(self):
        """Initialize job data service."""
        self.repository = job_listing_repository
        self.mapper = JobMapper()

    def save_stage_results(
        self,
        jobs: list[Job],
        company_name: str,
        stage_tag: str,
    ) -> int:
        """
        Save jobs to database after stage processing.

        This method will either create new job listings or update existing ones
        based on the job signature. It automatically tracks which stage has been completed.

        Args:
            jobs: List of Job objects to save
            company_name: Company name for logging
            stage_tag: Stage identifier (e.g., "stage_1", "stage_2")

        Returns:
            int: Number of jobs successfully saved

        Raises:
            Exception: If database operation fails
        """
        if not jobs:
            logger.warning(f"No jobs to save for {company_name} at {stage_tag}")
            return 0

        try:
            saved_count = 0
            failed_count = 0

            for job in jobs:
                try:
                    # Check if job already exists
                    existing = self.repository.get_by_signature(job.signature)

                    if existing:
                        # Update existing job listing
                        self.mapper.update_job_listing_from_job(existing, job)
                        if self.repository.update(existing):
                            saved_count += 1
                        else:
                            failed_count += 1
                            logger.warning(f"Failed to update job: {job.signature}")
                    else:
                        # Create new job listing
                        job_listing = self.mapper.to_job_listing(job)
                        created = self.repository.create(job_listing)
                        if created:
                            saved_count += 1
                        else:
                            failed_count += 1
                            logger.warning(f"Failed to create job: {job.signature}")

                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error saving job {job.signature}: {e}")

            logger.info(
                f"Saved {saved_count} jobs for {company_name} at {stage_tag}. "
                f"Failed: {failed_count}"
            )
            return saved_count

        except Exception as e:
            error_msg = f"Failed to save jobs for {company_name} at {stage_tag}: {e}"
            logger.error(error_msg)
            raise

    def load_jobs_for_stage(
        self,
        company_name: str,
        stage_tag: str,
    ) -> list[Job]:
        """
        Load jobs from database for a specific company and stage.

        This method loads jobs that are ready to be processed by the specified stage.
        For example, for stage_2, it loads jobs that have completed stage_1 but not stage_2.

        Args:
            company_name: Company name
            stage_tag: Stage identifier (e.g., "stage_2", "stage_3", "stage_4")

        Returns:
            List of Job objects ready for processing

        Raises:
            Exception: If database operation fails
        """
        try:
            # Determine which stage we're loading for
            stage_number = self._get_stage_number(stage_tag)

            if stage_number is None:
                logger.error(f"Invalid stage tag: {stage_tag}")
                return []

            # For stage 1, we don't load from database (fresh scraping)
            if stage_number == 1:
                logger.info("Stage 1 doesn't load from database")
                return []

            # Load jobs ready for this stage
            job_listings = self.repository.find_jobs_by_company_for_stage(
                company=company_name,
                stage=stage_number,
            )

            # Convert to Job objects
            jobs = [self.mapper.to_job(job_listing) for job_listing in job_listings]

            logger.info(
                f"Loaded {len(jobs)} jobs for {company_name} ready for {stage_tag}"
            )
            return jobs

        except Exception as e:
            error_msg = f"Failed to load jobs for {company_name} at {stage_tag}: {e}"
            logger.error(error_msg)
            raise

    def load_all_jobs_for_company(self, company_name: str) -> list[Job]:
        """
        Load all active jobs for a company regardless of stage.

        Args:
            company_name: Company name

        Returns:
            List of all Job objects for the company
        """
        try:
            job_listings = self.repository.find_by_company(company_name, limit=1000)
            jobs = [self.mapper.to_job(job_listing) for job_listing in job_listings]

            logger.info(f"Loaded {len(jobs)} total jobs for {company_name}")
            return jobs

        except Exception as e:
            error_msg = f"Failed to load all jobs for {company_name}: {e}"
            logger.error(error_msg)
            raise

    def get_existing_signatures(self, company_name: str) -> set[str]:
        """
        Get all existing job signatures for a company.

        This is useful for deduplication in Stage 1.

        Args:
            company_name: Company name

        Returns:
            Set of job signatures
        """
        try:
            job_listings = self.repository.find_by_company(company_name, limit=10000)
            signatures = {job.signature for job in job_listings}

            logger.info(
                f"Found {len(signatures)} existing signatures for {company_name}"
            )
            return signatures

        except Exception as e:
            logger.error(f"Error getting signatures for {company_name}: {e}")
            return set()

    def deactivate_missing_jobs(
        self, company_name: str, current_signatures: set[str]
    ) -> int:
        """
        Deactivate jobs that are no longer present in the current scrape.

        This helps track jobs that have been removed from company career pages.

        Args:
            company_name: Company name
            current_signatures: Set of signatures from current scrape

        Returns:
            int: Number of jobs deactivated
        """
        try:
            # Get all active jobs for company
            active_jobs = self.repository.find_by_filters(
                company=company_name,
                active=True,
                limit=10000,
            )

            deactivated_count = 0

            for job_listing in active_jobs:
                if job_listing.signature not in current_signatures:
                    job_listing.deactivate()
                    if self.repository.update(job_listing):
                        deactivated_count += 1

            logger.info(f"Deactivated {deactivated_count} jobs for {company_name}")
            return deactivated_count

        except Exception as e:
            logger.error(f"Error deactivating jobs for {company_name}: {e}")
            return 0

    def get_stage_statistics(self, company_name: str | None = None) -> dict[str, Any]:
        """
        Get statistics about stage completion.

        Args:
            company_name: Optional company name to filter by

        Returns:
            dict: Statistics about stage completion
        """
        try:
            stats: dict[str, Any] = self.repository.count_by_stage()

            if company_name:
                # Add company-specific stats
                company_jobs = self.repository.find_by_company(
                    company_name, limit=10000
                )

                # Get today's date range for filtering (in local timezone)
                today_start = now_utc().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                today_end = now_utc().replace(
                    hour=23, minute=59, second=59, microsecond=999999
                )

                stats["company"] = company_name
                stats["new_jobs"] = sum(
                    1
                    for j in company_jobs
                    if j.created_at.replace(tzinfo=UTC_TZ) >= today_start
                    and j.created_at.replace(tzinfo=UTC_TZ) <= today_end
                )
                stats["active_jobs"] = sum(1 for j in company_jobs if j.active)
                stats["inactive_jobs"] = sum(1 for j in company_jobs if not j.active)
                stats["jobs_deactivated"] = sum(
                    1
                    for j in company_jobs
                    if not j.active
                    and j.updated_at.replace(tzinfo=UTC_TZ) >= today_start
                    and j.updated_at.replace(tzinfo=UTC_TZ) <= today_end
                )

            return stats

        except Exception as e:
            logger.error(f"Error getting stage statistics: {e}")
            return {}

    def _get_stage_number(self, stage_tag: str) -> int | None:
        """
        Extract stage number from stage tag.

        Args:
            stage_tag: Stage identifier (e.g., "stage_1", "stage_2")

        Returns:
            int: Stage number or None if invalid
        """
        try:
            # Handle both "stage_1" and "1" formats
            if stage_tag.startswith("stage_"):
                return int(stage_tag.split("_")[1])
            return int(stage_tag)
        except (ValueError, IndexError):
            return None

    def remove_incomplete_jobs(self, company_name: str) -> int:
        """
        Remove all jobs for a company that haven't completed all pipeline stages.

        A job is considered incomplete if any of stage_2_completed, stage_3_completed,
        or stage_4_completed is False.

        Args:
            company_name: Company name

        Returns:
            int: Number of jobs removed

        Raises:
            Exception: If database operation fails
        """
        try:
            removed_count = self.repository.delete_incomplete_jobs_by_company(
                company_name
            )

            if removed_count > 0:
                logger.info(
                    f"Removed {removed_count} incomplete jobs for {company_name}"
                )

            return int(removed_count)

        except Exception as e:
            error_msg = f"Failed to remove incomplete jobs for {company_name}: {e}"
            logger.error(error_msg)
            raise
