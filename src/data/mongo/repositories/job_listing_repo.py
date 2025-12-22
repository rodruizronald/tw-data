import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from bson import ObjectId
from pymongo.errors import PyMongoError

from core.config.database import mongodb_config
from data.mongo.controller import DatabaseController
from data.mongo.models.job_listing import JobListing
from data.mongo.repositories.base_repo import BaseRepository
from utils.timezone import now_utc

if TYPE_CHECKING:
    from pymongo.results import DeleteResult


logger = logging.getLogger(__name__)

"""
Repository layer for job listing CRUD operations.

This module provides the repository pattern implementation for JobListing
with comprehensive CRUD operations, querying, and business logic methods.
"""


class JobListingRepository(BaseRepository[JobListing]):
    """
    Repository for JobListing CRUD operations following repository pattern.

    Provides high-level database operations with error handling, logging,
    and business logic encapsulation.
    """

    def __init__(self, db_controller: DatabaseController) -> None:
        super().__init__(db_controller, mongodb_config.job_listings_collection)

    # Implement abstract methods
    def _to_dict(self, model: JobListing) -> dict[str, Any]:
        """Convert model to dictionary for storage."""
        result: dict[str, Any] = model.to_dict()
        return result

    def _from_dict(self, data: dict[str, Any]) -> JobListing:
        return JobListing.from_dict(data)

    def _get_unique_key(self, model: JobListing) -> str:
        """Get unique identifier for logging."""
        signature: str = model.signature
        return signature

    def _get_id(self, model: JobListing) -> ObjectId | None:
        """Get MongoDB _id from model."""
        _id: ObjectId | None = model._id
        return _id

    def _set_id(self, model: JobListing, object_id: ObjectId) -> None:
        model._id = object_id

    # Domain-specific methods
    def get_by_signature(self, signature: str) -> JobListing | None:
        """
        Retrieve job listing by unique signature.

        Args:
            signature: Unique job signature

        Returns:
            JobListing: Found job listing or None
        """
        try:
            doc = self.collection.find_one({"signature": signature})
            if doc:
                return JobListing.from_dict(doc)
            return None
        except PyMongoError as e:
            logger.error(f"Error retrieving job listing by signature {signature}: {e}")
            return None

    def delete_by_signature(self, signature: str) -> bool:
        """
        Delete job listing by signature.

        Args:
            signature: Unique job signature

        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            result: DeleteResult = self.collection.delete_one({"signature": signature})

            if result.deleted_count > 0:
                logger.info(f"Deleted job listing with signature: {signature}")
                return True
            else:
                logger.warning(f"No job listing found with signature: {signature}")
                return False

        except PyMongoError as e:
            logger.error(f"Error deleting job listing with signature {signature}: {e}")
            return False

    def find_by_company(self, company: str, limit: int = 100) -> list[JobListing]:
        """
        Find job listings by company name.

        Args:
            company: Company name
            limit: Maximum number of results

        Returns:
            list[JobListing]: List of matching job listings
        """
        try:
            cursor = self.collection.find({"company": company}).limit(limit)
            return [JobListing.from_dict(doc) for doc in cursor]
        except PyMongoError as e:
            logger.error(f"Error finding job listings by company {company}: {e}")
            return []

    def find_active_jobs(self, limit: int = 100) -> list[JobListing]:
        """
        Find active job listings.

        Args:
            limit: Maximum number of results

        Returns:
            list[JobListing]: List of active job listings
        """
        try:
            cursor = self.collection.find({"active": True}).limit(limit)
            return [JobListing.from_dict(doc) for doc in cursor]
        except PyMongoError as e:
            logger.error(f"Error finding active job listings: {e}")
            return []

    def find_inactive_jobs(self, limit: int = 100) -> list[JobListing]:
        """
        Find inactive job listings.

        Args:
            limit: Maximum number of results

        Returns:
            list[JobListing]: List of inactive job listings
        """
        try:
            cursor = self.collection.find({"active": False}).limit(limit)
            return [JobListing.from_dict(doc) for doc in cursor]
        except PyMongoError as e:
            logger.error(f"Error finding inactive job listings: {e}")
            return []

    def find_by_filters(
        self,
        company: str | None = None,
        location: str | None = None,
        work_mode: str | None = None,
        employment_type: str | None = None,
        experience_level: str | None = None,
        technologies: list[str] | None = None,
        active: bool | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[JobListing]:
        """
        Find job listings with multiple filters.

        Args:
            company: Company name filter
            location: Location filter
            work_mode: Work mode filter
            employment_type: Employment type filter
            experience_level: Experience level filter
            technologies: List of required technologies
            active: Active status filter
            limit: Maximum number of results
            skip: Number of results to skip (for pagination)

        Returns:
            list[JobListing]: List of matching job listings
        """
        try:
            query: dict[str, Any] = {}

            # Add filters
            if company:
                query["company"] = {"$regex": company, "$options": "i"}

            if location:
                query["location"] = location

            if work_mode:
                query["work_mode"] = work_mode

            if employment_type:
                query["employment_type"] = employment_type

            if experience_level:
                query["experience_level"] = experience_level

            if technologies:
                query["main_technologies"] = {"$in": technologies}

            if active is not None:
                query["active"] = active

            cursor = self.collection.find(query).skip(skip).limit(limit)
            return [JobListing.from_dict(doc) for doc in cursor]
        except PyMongoError as e:
            logger.error(f"Error finding job listings with filters: {e}")
            return []

    def count_active(self) -> int:
        """
        Count active job listings.

        Returns:
            int: Count of active job listings
        """
        try:
            count: int = self.collection.count_documents({"active": True})
            return count
        except PyMongoError as e:
            logger.error(f"Error counting active job listings: {e}")
            return 0

    def count_inactive(self) -> int:
        """
        Count inactive job listings.

        Returns:
            int: Count of inactive job listings
        """
        try:
            count: int = self.collection.count_documents({"active": False})
            return count
        except PyMongoError as e:
            logger.error(f"Error counting inactive job listings: {e}")
            return 0

    def get_companies_stats(self) -> dict[str, int]:
        """
        Get job count statistics by company.

        Returns:
            dict[str, int]: Dictionary with company name as key and count as value
        """
        try:
            pipeline: list[dict[str, Any]] = [
                {"$group": {"_id": "$company", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
            ]

            result = {}
            for doc in self.collection.aggregate(pipeline):
                result[doc["_id"]] = doc["count"]

            return result
        except PyMongoError as e:
            logger.error(f"Error getting company statistics: {e}")
            return {}

    def find_jobs_for_stage(self, stage: int, limit: int = 100) -> list[JobListing]:
        """
        Find jobs that need processing for a specific stage.

        Args:
            stage: Stage number (2, 3, 4, or 5)
            limit: Maximum number of results

        Returns:
            list[JobListing]: List of jobs ready for the specified stage
        """
        try:
            query: dict[str, Any] = {"active": True}

            if stage == 2:
                query["stage_1_completed"] = True
                query["stage_2_completed"] = False
            elif stage == 3:
                query["stage_1_completed"] = True
                query["stage_2_completed"] = True
                query["stage_3_completed"] = False
            elif stage == 4:
                query["stage_1_completed"] = True
                query["stage_2_completed"] = True
                query["stage_3_completed"] = True
                query["stage_4_completed"] = False
            elif stage == 5:
                query["stage_1_completed"] = True
                query["stage_2_completed"] = True
                query["stage_3_completed"] = True
                query["stage_4_completed"] = True
                query["stage_5_completed"] = False
            else:
                logger.warning(f"Invalid stage number: {stage}")
                return []

            cursor = self.collection.find(query).limit(limit)
            jobs = [JobListing.from_dict(doc) for doc in cursor]
            logger.info(f"Found {len(jobs)} jobs ready for stage {stage}")
            return jobs

        except PyMongoError as e:
            logger.error(f"Error finding jobs for stage {stage}: {e}")
            return []

    def find_jobs_by_company_for_stage(
        self, company: str, stage: int, limit: int = 100
    ) -> list[JobListing]:
        """
        Find jobs for a specific company that need processing for a specific stage.

        Args:
            company: Company name
            stage: Stage number (2, 3, 4, or 5)
            limit: Maximum number of results

        Returns:
            list[JobListing]: List of jobs ready for the specified stage
        """
        try:
            # Get today's date range in UTC
            today_start = now_utc().replace(hour=0, minute=0, second=0, microsecond=0)

            query: dict[str, Any] = {
                "active": True,
                "company": company,
                "created_at": {"$gte": today_start},
            }

            if stage == 2:
                query["stage_1_completed"] = True
                query["stage_2_completed"] = False
                query["stage_3_completed"] = False
                query["stage_4_completed"] = False
                query["stage_5_completed"] = False
            elif stage == 3:
                query["stage_1_completed"] = True
                query["stage_2_completed"] = True
                query["stage_3_completed"] = False
                query["stage_4_completed"] = False
                query["stage_5_completed"] = False
            elif stage == 4:
                query["stage_1_completed"] = True
                query["stage_2_completed"] = True
                query["stage_3_completed"] = True
                query["stage_4_completed"] = False
                query["stage_5_completed"] = False
            elif stage == 5:
                query["stage_1_completed"] = True
                query["stage_2_completed"] = True
                query["stage_3_completed"] = True
                query["stage_4_completed"] = True
                query["stage_5_completed"] = False
            else:
                logger.warning(f"Invalid stage number: {stage}")
                return []

            cursor = self.collection.find(query).limit(limit)
            jobs = [JobListing.from_dict(doc) for doc in cursor]
            logger.info(f"Found {len(jobs)} jobs for {company} ready for stage {stage}")
            return jobs

        except PyMongoError as e:
            logger.error(f"Error finding jobs for {company} at stage {stage}: {e}")
            return []

    def count_by_stage(self) -> dict[str, int]:
        """
        Count jobs by stage completion.

        Returns:
            dict[str, int]: Dictionary with stage completion statistics
        """
        try:
            return {
                "stage_1_only": self.collection.count_documents(
                    {
                        "stage_1_completed": True,
                        "stage_2_completed": False,
                    }
                ),
                "stage_2_completed": self.collection.count_documents(
                    {"stage_2_completed": True, "stage_3_completed": False}
                ),
                "stage_3_completed": self.collection.count_documents(
                    {"stage_3_completed": True, "stage_4_completed": False}
                ),
                "stage_4_completed": self.collection.count_documents(
                    {"stage_4_completed": True, "stage_5_completed": False}
                ),
                "stage_5_completed": self.collection.count_documents(
                    {"stage_5_completed": True}
                ),
                "fully_processed": self.collection.count_documents(
                    {
                        "stage_2_completed": True,
                        "stage_3_completed": True,
                        "stage_4_completed": True,
                        "stage_5_completed": True,
                    }
                ),
            }
        except PyMongoError as e:
            logger.error(f"Error counting jobs by stage: {e}")
            return {}

    def cleanup_old_entries(self, days: int = 30) -> int:
        """
        Delete job listings older than specified days.

        Args:
            days: Number of days (job listings older than this will be deleted)

        Returns:
            int: Number of deleted job listings
        """
        try:
            # Calculate cutoff in UTC (simpler and more efficient)
            cutoff_datetime = now_utc() - timedelta(days=days)

            result: DeleteResult = self.collection.delete_many(
                {"created_at": {"$lt": cutoff_datetime}}
            )

            deleted_count = result.deleted_count
            logger.info(
                f"Cleaned up {deleted_count} old job listings (older than {days} days)"
            )
            return deleted_count

        except PyMongoError as e:
            logger.error(f"Error cleaning up old job listings: {e}")
            return 0

    def delete_incomplete_jobs_by_company(self, company: str) -> int:
        """
        Delete all jobs for a company that haven't completed all pipeline stages.

        Args:
            company: Company name to filter by

        Returns:
            int: Number of deleted job listings
        """
        try:
            query = {
                "company": company,
                "$or": [
                    {"stage_2_completed": False},
                    {"stage_3_completed": False},
                    {"stage_4_completed": False},
                    {"stage_5_completed": False},
                ],
            }

            result: DeleteResult = self.collection.delete_many(query)
            return result.deleted_count

        except PyMongoError as e:
            logger.error(f"Error deleting incomplete jobs for {company}: {e}")
            return 0
