"""
Job Metrics Service for business-level pipeline metrics.

Provides the primary interface for pipeline components to record and query metrics.
Handles business logic for metric calculation, aggregation, and validation.
"""

import calendar
import logging
import time
from collections.abc import Callable
from typing import Any

from core.models.metrics import CompanySummaryInput, StageMetricsInput
from data.mongo import (
    job_aggregate_metrics_repository,
    job_daily_metrics_repository,
)
from data.mongo.mappers.metrics_mapper import MetricsMapper
from data.mongo.models.aggregate_metrics import (
    DailyAggregateMetrics,
)
from data.mongo.models.daily_metrics import (
    CompanyDailyMetrics,
)
from utils.timezone import now_utc

logger = logging.getLogger(__name__)


class JobMetricsService:
    """
    Service for managing job metrics operations.

    Provides business logic layer between pipeline and repositories.
    Thread-safe for concurrent company processing.
    """

    # Retry configuration
    MAX_RETRIES = 2
    INITIAL_RETRY_DELAY = 1.0  # seconds
    BACKOFF_FACTOR = 2.0

    def __init__(self):
        """
        Initialize job metrics service.
        """
        self.daily_repository = job_daily_metrics_repository
        self.aggregate_repository = job_aggregate_metrics_repository
        self.mapper = MetricsMapper()

    def record_stage_metrics(
        self,
        company_name: str,
        stage: str,
        metrics_input: StageMetricsInput,
        date: str | None = None,
    ) -> None:
        """
        Record metrics for a specific stage completion.

        Converts stage input to repository model before storage.
        Includes retry logic with exponential backoff.

        Args:
            company_name: Company name
            stage: Stage identifier (e.g., "stage_1", "stage_2", or "1", "2")
            metrics_input: StageMetricsInput model object
            date: Optional date override (default: today)
        """
        if date is None:
            date = now_utc().strftime("%Y-%m-%d")

        # Extract stage number
        stage_number = self._get_stage_number(stage)
        if stage_number is None:
            logger.error(f"Invalid stage identifier: {stage}")
            return

        try:
            # Map input model to repository model
            stage_metrics = self.mapper.stage_input_to_stage_metrics(metrics_input)

            # Attempt to update with retries
            success = self._retry_operation(
                lambda: self.daily_repository.update_stage_metrics(
                    date, company_name, stage_number, stage_metrics
                ),
                operation_name=f"record_stage_metrics for {company_name} stage {stage_number}",
            )

            if success:
                logger.info(
                    f"Recorded stage {stage_number} metrics for {company_name}: "
                    f"{metrics_input.jobs_completed}/{metrics_input.jobs_processed} jobs completed"
                )
            else:
                logger.warning(
                    f"Failed to record stage {stage_number} metrics for {company_name} after retries"
                )

        except Exception as e:
            logger.error(
                f"Error recording stage metrics for {company_name} stage {stage}: {e}"
            )

    def record_company_completion(
        self,
        company_name: str,
        summary_input: CompanySummaryInput,
        date: str | None = None,
    ) -> None:
        """
        Record final metrics when company processing completes.

        Updates overall status and company-level metrics.

        Args:
            company_name: Company name
            summary_input: CompanySummaryInput model object
            date: Optional date override (default: today)
        """
        if date is None:
            date = now_utc().strftime("%Y-%m-%d")

        try:
            # Map input model to repository model
            company_metrics = self.mapper.summary_input_to_company_metrics(
                summary_input, date, company_name
            )

            # Attempt to update with retries
            success = self._retry_operation(
                lambda: self.daily_repository.update_company_summary(
                    date, company_name, company_metrics
                ),
                operation_name=f"record_company_completion for {company_name}",
            )

            if success:
                logger.info(
                    f"Recorded company completion for {company_name}: "
                    f"status={summary_input.overall_status}, "
                    f"new_jobs={summary_input.new_jobs_found}"
                )
            else:
                logger.warning(
                    f"Failed to record company completion for {company_name} after retries"
                )

        except Exception as e:
            logger.error(f"Error recording company completion for {company_name}: {e}")

    def calculate_daily_aggregates(self, date: str | None = None) -> None:
        """
        Calculate and store daily aggregated metrics.

        Aggregates all company metrics for the given date into a single
        pipeline-wide metrics document.

        Args:
            date: Date in YYYY-MM-DD format (default: today)
        """
        if date is None:
            date = now_utc().strftime("%Y-%m-%d")

        try:
            logger.info(f"Calculating daily aggregates for {date}...")

            # Get aggregated data from daily repository
            aggregated_data = self.daily_repository.aggregate_by_date(date)

            if not aggregated_data:
                logger.warning(f"No data found to aggregate for {date}")
                return

            # Calculate derived metrics
            total_companies = aggregated_data.get("total_companies", 0)
            companies_successful = aggregated_data.get("companies_successful", 0)

            overall_success_rate = (
                (companies_successful / total_companies * 100.0)
                if total_companies > 0
                else 0.0
            )

            net_job_change = aggregated_data.get(
                "total_new_jobs", 0
            ) - aggregated_data.get("total_jobs_deactivated", 0)

            # Calculate stage success rates
            stage_success_rates = {}
            for stage in range(1, 6):  # Changed from range(1, 5)
                processed = aggregated_data.get(f"stage_{stage}_processed", 0)
                completed = aggregated_data.get(f"stage_{stage}_completed", 0)
                stage_success_rates[f"stage_{stage}_success_rate"] = (
                    (completed / processed * 100.0) if processed > 0 else 0.0
                )

            # Create aggregate metrics object
            aggregate_metrics = DailyAggregateMetrics(
                date=date,
                total_companies_processed=total_companies,
                companies_successful=companies_successful,
                companies_partial=aggregated_data.get("companies_partial", 0),
                companies_with_failures=aggregated_data.get("companies_failed", 0),
                overall_success_rate=overall_success_rate,
                total_new_jobs=aggregated_data.get("total_new_jobs", 0),
                total_jobs_deactivated=aggregated_data.get("total_jobs_deactivated", 0),
                total_active_jobs=aggregated_data.get("total_active_jobs", 0),
                total_inactive_jobs=aggregated_data.get("total_inactive_jobs", 0),
                net_job_change=net_job_change,
                stage_1_total_processed=aggregated_data.get("stage_1_processed", 0),
                stage_1_success_rate=stage_success_rates.get(
                    "stage_1_success_rate", 0.0
                ),
                stage_1_avg_execution_seconds=aggregated_data.get(
                    "stage_1_avg_execution_seconds", 0.0
                ),
                stage_2_total_processed=aggregated_data.get("stage_2_processed", 0),
                stage_2_success_rate=stage_success_rates.get(
                    "stage_2_success_rate", 0.0
                ),
                stage_2_avg_execution_seconds=aggregated_data.get(
                    "stage_2_avg_execution_seconds", 0.0
                ),
                stage_3_total_processed=aggregated_data.get("stage_3_processed", 0),
                stage_3_success_rate=stage_success_rates.get(
                    "stage_3_success_rate", 0.0
                ),
                stage_3_avg_execution_seconds=aggregated_data.get(
                    "stage_3_avg_execution_seconds", 0.0
                ),
                stage_4_total_processed=aggregated_data.get("stage_4_processed", 0),
                stage_4_success_rate=stage_success_rates.get(
                    "stage_4_success_rate", 0.0
                ),
                stage_4_avg_execution_seconds=aggregated_data.get(
                    "stage_4_avg_execution_seconds", 0.0
                ),
                pipeline_run_count=total_companies,
                calculation_timestamp=now_utc(),
            )

            # Store aggregate metrics
            success = self._retry_operation(
                lambda: self.aggregate_repository.upsert_daily_aggregate(
                    date, aggregate_metrics
                ),
                operation_name=f"calculate_daily_aggregates for {date}",
            )

            if success:
                logger.info(
                    f"Calculated daily aggregates for {date}: "
                    f"{total_companies} companies, "
                    f"{overall_success_rate:.1f}% success rate"
                )
            else:
                logger.warning(
                    f"Failed to store daily aggregates for {date} after retries"
                )

        except Exception as e:
            logger.error(f"Error calculating daily aggregates for {date}: {e}")

    def get_company_metrics(
        self,
        company_name: str,
        start_date: str,
        end_date: str,
    ) -> list[CompanyDailyMetrics]:
        """
        Retrieve metrics for a company within date range.

        Args:
            company_name: Company name
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            List of daily metric documents
        """
        try:
            metrics: list[CompanyDailyMetrics] = (
                self.daily_repository.find_by_date_range(
                    start_date, end_date, company_name
                )
            )

            logger.debug(
                f"Retrieved {len(metrics)} metrics for {company_name} "
                f"between {start_date} and {end_date}"
            )
            return metrics

        except Exception as e:
            logger.error(f"Error retrieving metrics for {company_name}: {e}")
            return []

    def get_pipeline_health_metrics(self, date: str) -> DailyAggregateMetrics | None:
        """
        Retrieve pipeline health metrics for a specific date.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Daily aggregate document or None
        """
        try:
            aggregate: DailyAggregateMetrics | None = (
                self.aggregate_repository.find_daily_aggregate(date)
            )

            if aggregate:
                logger.debug(f"Retrieved pipeline health metrics for {date}")
            else:
                logger.debug(f"No pipeline health metrics found for {date}")

            return aggregate

        except Exception as e:
            logger.error(f"Error retrieving pipeline health metrics: {e}")
            return None

    def get_companies_by_status(self, date: str, status: str) -> list[str]:
        """
        Get list of companies with specific status on given date.

        Args:
            date: Date in YYYY-MM-DD format
            status: Status to filter by (success|partial|failed)

        Returns:
            List of company names
        """
        try:
            companies: list[str] = self.daily_repository.get_companies_by_status(
                date, status
            )
            return companies if companies else []
        except Exception as e:
            logger.error(
                f"Error getting companies by status for {date}, status={status}: {e}"
            )
            return []

    def get_companies_by_date(
        self,
        date: str,
    ) -> list[CompanyDailyMetrics]:
        """
        Retrieve all company metrics for a specific date.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            List of CompanyDailyMetrics objects
        """
        try:
            companies: list[CompanyDailyMetrics] = (
                self.daily_repository.find_by_date_range(
                    start_date=date,
                    end_date=date,
                    company_name=None,  # Get all companies
                )
            )

            logger.debug(f"Retrieved {len(companies)} companies for {date}")
            return companies

        except Exception as e:
            logger.error(f"Error retrieving companies for {date}: {e}")
            return []

    def get_heatmap_data(
        self,
        year: int,
        month: int,
    ) -> list[dict[str, Any]]:
        """
        Get lightweight heatmap data for calendar visualization.

        Args:
            year: Year (e.g., 2024)
            month: Month (1-12)

        Returns:
            List of dicts with date, success_rate, and company_count
        """
        try:
            # Calculate date range for the month
            _, last_day = calendar.monthrange(year, month)
            start_date = f"{year:04d}-{month:02d}-01"
            end_date = f"{year:04d}-{month:02d}-{last_day:02d}"

            # Query aggregate repository
            aggregates = self.aggregate_repository.find_aggregates_by_date_range(
                start_date=start_date,
                end_date=end_date,
            )

            # Transform to lightweight format
            heatmap_data = [
                {
                    "date": agg.date,
                    "success_rate": agg.overall_success_rate,
                    "company_count": agg.total_companies_processed,
                }
                for agg in aggregates
            ]

            logger.debug(
                f"Retrieved heatmap data for {year}-{month:02d}: "
                f"{len(heatmap_data)} days"
            )
            return heatmap_data

        except Exception as e:
            logger.error(f"Error retrieving heatmap data: {e}")
            return []

    def get_most_recent_date(self) -> str | None:
        """
        Get the most recent date with aggregate metrics.

        Returns:
            Date string in YYYY-MM-DD format or None
        """
        try:
            # Query for most recent aggregate
            result = self.aggregate_repository.find_most_recent()

            if result:
                date: str = result.date
                logger.debug(f"Most recent date: {date}")
                return date

            logger.warning("No aggregate metrics found in database")
            return None

        except Exception as e:
            logger.error(f"Error finding most recent date: {e}")
            return None

    def _get_stage_number(self, stage_tag: str) -> int | None:
        """
        Extract stage number from stage tag.

        Args:
            stage_tag: Stage identifier (e.g., "stage_1", "1")

        Returns:
            Stage number or None if invalid
        """
        try:
            # Handle both "stage_1" and "1" formats
            if stage_tag.startswith("stage_"):
                return int(stage_tag.split("_")[1])
            return int(stage_tag)
        except (ValueError, IndexError):
            return None

    def _retry_operation(
        self,
        operation: Callable[[], bool],
        operation_name: str,
    ) -> bool:
        """
        Execute operation with exponential backoff retry.

        Args:
            operation: Function to execute
            operation_name: Name for logging

        Returns:
            True if operation succeeded, False otherwise
        """
        delay = self.INITIAL_RETRY_DELAY

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                result = operation()
                if result:
                    return True

                # Operation returned False but didn't raise exception
                if attempt < self.MAX_RETRIES:
                    logger.warning(
                        f"{operation_name} returned False, "
                        f"retrying in {delay}s... (attempt {attempt + 1}/{self.MAX_RETRIES + 1})"
                    )
                    time.sleep(delay)
                    delay *= self.BACKOFF_FACTOR

            except Exception as e:
                if attempt < self.MAX_RETRIES:
                    logger.warning(
                        f"{operation_name} failed: {e}. "
                        f"Retrying in {delay}s... (attempt {attempt + 1}/{self.MAX_RETRIES + 1})"
                    )
                    time.sleep(delay)
                    delay *= self.BACKOFF_FACTOR
                else:
                    logger.error(
                        f"{operation_name} failed after {self.MAX_RETRIES + 1} attempts: {e}"
                    )

        return False


# Global singleton instance
job_metrics_service = JobMetricsService()
