"""
Repository for daily job metrics persistence.

Handles database operations for company daily metrics without business logic.
Provides thread-safe access to MongoDB for concurrent company processing.
"""

import logging
from typing import Any

from bson import ObjectId
from pymongo.errors import PyMongoError

from core.config.database import mongodb_config
from data.mongo.controller import DatabaseController
from data.mongo.models.daily_metrics import CompanyDailyMetrics, StageMetrics
from utils.timezone import now_utc

from .base_repo import BaseRepository

logger = logging.getLogger(__name__)


class DailyMetricsRepository(BaseRepository[CompanyDailyMetrics]):
    """
    Repository for daily job metrics database operations.

    Thread-safe repository for storing and retrieving company daily metrics.
    MongoDB connection pooling ensures safe concurrent access.
    """

    def __init__(
        self,
        db_controller: DatabaseController,
    ):
        """
        Initialize daily metrics repository.

        Args:
            db_controller: Database controller instance
            collection_name: Name of daily metrics collection
        """
        super().__init__(db_controller, mongodb_config.job_metrics_daily_collection)

    # Implement abstract methods from BaseRepository
    def _to_dict(self, model: CompanyDailyMetrics) -> dict[str, Any]:
        """Convert model to dictionary for storage."""
        result: dict[str, Any] = model.to_dict()
        return result

    def _from_dict(self, data: dict[str, Any]) -> CompanyDailyMetrics:
        """Convert dictionary to model."""
        return CompanyDailyMetrics.from_dict(data)

    def _get_unique_key(self, model: CompanyDailyMetrics) -> str:
        """Get unique identifier for logging."""
        return f"{model.date}_{model.company_name}"

    def _get_id(self, model: CompanyDailyMetrics) -> ObjectId | None:
        """Get MongoDB _id from model."""
        _id: ObjectId | None = model._id
        return _id

    def _set_id(self, model: CompanyDailyMetrics, object_id: ObjectId) -> None:
        """Set MongoDB _id on model."""
        model._id = object_id

    # Domain-specific methods
    def upsert_company_daily_metrics(
        self, date: str, company_name: str, metrics: CompanyDailyMetrics
    ) -> bool:
        """
        Create or update daily metrics document for a company.

        Uses upsert with $set operators for atomic updates.
        Thread-safe for concurrent company processing.

        Args:
            date: Date in YYYY-MM-DD format
            company_name: Company name
            metrics: Company daily metrics object

        Returns:
            True if successful, False otherwise
        """
        try:
            # Update the timestamps
            metrics.updated_at = now_utc()

            # Convert to flat dictionary
            metrics_dict = metrics.to_dict()
            metrics_dict.pop("_id", None)

            # Use upsert to create or update
            result = self.collection.update_one(
                {"date": date, "company_name": company_name},
                {
                    "$set": metrics_dict,
                    "$setOnInsert": {"created_at": metrics.created_at},
                },
                upsert=True,
            )

            if result.upserted_id or result.modified_count > 0:
                logger.debug(
                    f"Upserted metrics for {company_name} on {date}. "
                    f"Upserted: {result.upserted_id is not None}, "
                    f"Modified: {result.modified_count}"
                )
                return True

            return False

        except PyMongoError as e:
            logger.error(
                f"Error upserting company daily metrics for {company_name} on {date}: {e}"
            )
            return False

    def update_stage_metrics(
        self,
        date: str,
        company_name: str,
        stage_number: int,
        stage_metrics: StageMetrics,
    ) -> bool:
        """
        Update specific stage fields within daily document.

        Uses flat field names for direct MongoDB updates.
        Thread-safe atomic update operation.

        Args:
            date: Date in YYYY-MM-DD format
            company_name: Company name
            stage_number: Stage number (1-5)
            stage_metrics: StageMetrics model object

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert StageMetrics to dict
            stage_data = stage_metrics.to_dict()

            # Build update document with flat field names
            update_fields = {}
            for key, value in stage_data.items():
                flat_key = f"stage_{stage_number}_{key}"
                update_fields[flat_key] = value

            # Always update the updated_at and last_updated_stage
            update_fields["updated_at"] = now_utc()
            update_fields["last_updated_stage"] = f"stage_{stage_number}"

            # Perform atomic update with upsert
            result = self.collection.update_one(
                {"date": date, "company_name": company_name},
                {
                    "$set": update_fields,
                    "$setOnInsert": {
                        "date": date,
                        "company_name": company_name,
                        "document_type": "company_daily",
                        "created_at": now_utc(),
                    },
                },
                upsert=True,
            )

            if result.upserted_id or result.modified_count > 0:
                logger.debug(
                    f"Updated stage {stage_number} metrics for {company_name} on {date}"
                )
                return True

            return False

        except PyMongoError as e:
            logger.error(
                f"Error updating stage {stage_number} metrics for {company_name} on {date}: {e}"
            )
            return False

    def update_company_summary(
        self, date: str, company_name: str, summary_metrics: CompanyDailyMetrics
    ) -> bool:
        """
        Update company-level summary fields.

        Args:
            date: Date in YYYY-MM-DD format
            company_name: Company name
            summary_metrics: CompanyDailyMetrics model object

        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract only the summary fields we want to update
            summary_data = {
                "new_jobs_found": summary_metrics.new_jobs_found,
                "total_active_jobs": summary_metrics.total_active_jobs,
                "total_inactive_jobs": summary_metrics.total_inactive_jobs,
                "jobs_deactivated_today": summary_metrics.jobs_deactivated_today,
                "overall_status": summary_metrics.overall_status,
                "updated_at": now_utc(),
            }

            # Add optional fields if present
            if summary_metrics.prefect_flow_run_id:
                summary_data["prefect_flow_run_id"] = (
                    summary_metrics.prefect_flow_run_id
                )
            if summary_metrics.pipeline_version:
                summary_data["pipeline_version"] = summary_metrics.pipeline_version

            result = self.collection.update_one(
                {"date": date, "company_name": company_name},
                {
                    "$set": summary_data,
                    "$setOnInsert": {
                        "date": date,
                        "company_name": company_name,
                        "document_type": "company_daily",
                        "created_at": now_utc(),
                    },
                },
                upsert=True,
            )

            if result.upserted_id or result.modified_count > 0:
                logger.debug(f"Updated company summary for {company_name} on {date}")
                return True

            return False

        except PyMongoError as e:
            logger.error(
                f"Error updating company summary for {company_name} on {date}: {e}"
            )
            return False

    def find_by_date_range(
        self,
        start_date: str,
        end_date: str,
        company_name: str | None = None,
    ) -> list[CompanyDailyMetrics]:
        """
        Query metrics within date range.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            company_name: Optional company name filter

        Returns:
            List of company daily metrics
        """
        try:
            query: dict[str, Any] = {"date": {"$gte": start_date, "$lte": end_date}}

            if company_name:
                query["company_name"] = company_name

            cursor = self.collection.find(query).sort("date", -1)

            results = [CompanyDailyMetrics(**doc) for doc in cursor]

            logger.debug(
                f"Found {len(results)} metrics between {start_date} and {end_date}"
                + (f" for {company_name}" if company_name else "")
            )
            return results

        except PyMongoError as e:
            logger.error(f"Error querying metrics by date range: {e}")
            return []

    def find_by_company_and_date(
        self, company_name: str, date: str
    ) -> CompanyDailyMetrics | None:
        """
        Find metrics for a specific company and date.

        Args:
            company_name: Company name
            date: Date in YYYY-MM-DD format

        Returns:
            Company daily metrics or None
        """
        try:
            doc = self.collection.find_one({"date": date, "company_name": company_name})

            if doc:
                return CompanyDailyMetrics(**doc)

            return None

        except PyMongoError as e:
            logger.error(f"Error finding metrics for {company_name} on {date}: {e}")
            return None

    def get_companies_by_status(self, date: str, status: str) -> list[str]:
        """
        Find all companies with specific status on given date.

        Args:
            date: Date in YYYY-MM-DD format
            status: Status to filter by (success|partial|failed)

        Returns:
            List of company names
        """
        try:
            cursor = self.collection.find(
                {"date": date, "overall_status": status}, {"company_name": 1}
            )

            companies = [doc["company_name"] for doc in cursor]
            logger.debug(
                f"Found {len(companies)} companies with status '{status}' on {date}"
            )
            return companies

        except PyMongoError as e:
            logger.error(f"Error getting companies by status: {e}")
            return []

    def aggregate_by_date(self, date: str) -> dict[str, Any]:
        """
        Perform aggregation queries for daily summaries.

        Calculates aggregate metrics for all companies on a given date.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Dictionary of calculated aggregate metrics
        """
        try:
            pipeline: list[dict[str, Any]] = [
                {"$match": {"date": date}},
                {
                    "$group": {
                        "_id": None,
                        "total_companies": {"$sum": 1},
                        "companies_successful": {
                            "$sum": {
                                "$cond": [{"$eq": ["$overall_status", "success"]}, 1, 0]
                            }
                        },
                        "companies_partial": {
                            "$sum": {
                                "$cond": [{"$eq": ["$overall_status", "partial"]}, 1, 0]
                            }
                        },
                        "companies_failed": {
                            "$sum": {
                                "$cond": [{"$eq": ["$overall_status", "failed"]}, 1, 0]
                            }
                        },
                        "total_new_jobs": {"$sum": "$new_jobs_found"},
                        "total_jobs_deactivated": {"$sum": "$jobs_deactivated_today"},
                        "total_active_jobs": {"$sum": "$total_active_jobs"},
                        "total_inactive_jobs": {"$sum": "$total_inactive_jobs"},
                        # Stage 1 aggregations
                        "stage_1_processed": {"$sum": "$stage_1_jobs_processed"},
                        "stage_1_completed": {"$sum": "$stage_1_jobs_completed"},
                        "stage_1_execution_times": {
                            "$push": "$stage_1_execution_seconds"
                        },
                        # Stage 2 aggregations
                        "stage_2_processed": {"$sum": "$stage_2_jobs_processed"},
                        "stage_2_completed": {"$sum": "$stage_2_jobs_completed"},
                        "stage_2_execution_times": {
                            "$push": "$stage_2_execution_seconds"
                        },
                        # Stage 3 aggregations
                        "stage_3_processed": {"$sum": "$stage_3_jobs_processed"},
                        "stage_3_completed": {"$sum": "$stage_3_jobs_completed"},
                        "stage_3_execution_times": {
                            "$push": "$stage_3_execution_seconds"
                        },
                        # Stage 4 aggregations
                        "stage_4_processed": {"$sum": "$stage_4_jobs_processed"},
                        "stage_4_completed": {"$sum": "$stage_4_jobs_completed"},
                        "stage_4_execution_times": {
                            "$push": "$stage_4_execution_seconds"
                        },
                        # Stage 5 aggregations
                        "stage_5_processed": {"$sum": "$stage_5_jobs_processed"},
                        "stage_5_completed": {"$sum": "$stage_5_jobs_completed"},
                        "stage_5_execution_times": {
                            "$push": "$stage_5_execution_seconds"
                        },
                    }
                },
            ]

            result = list(self.collection.aggregate(pipeline))

            if result:
                aggregated: dict[str, Any] = result[0]
                aggregated.pop("_id", None)

                # Calculate averages for execution times
                for stage in range(1, 6):
                    times_key = f"stage_{stage}_execution_times"
                    times = [t for t in aggregated.get(times_key, []) if t and t > 0]
                    aggregated[f"stage_{stage}_avg_execution_seconds"] = (
                        sum(times) / len(times) if times else 0.0
                    )
                    # Remove the raw times array
                    aggregated.pop(times_key, None)

                logger.debug(
                    f"Aggregated metrics for {date}: {aggregated.get('total_companies', 0)} companies"
                )
                return aggregated

            return {}

        except PyMongoError as e:
            logger.error(f"Error aggregating metrics for {date}: {e}")
            return {}
