"""
Mapper for converting between service layer and repository layer models.

This module provides mapping functions to transform metrics data between different layers:
- Service layer models (StageMetricsInput, CompanySummaryInput) - used by pipeline components
- Repository layer models (StageMetrics, CompanyDailyMetrics) - used for database operations

The mapper ensures clean separation of concerns and allows each layer to have
models optimized for its specific purpose.
"""

from core.models.metrics import CompanySummaryInput, StageMetricsInput
from data.mongo.models.daily_metrics import CompanyDailyMetrics, StageMetrics


class MetricsMapper:
    """Mapper to convert between service layer models and repository models."""

    @staticmethod
    def stage_input_to_stage_metrics(input_data: StageMetricsInput) -> StageMetrics:
        """Convert StageMetricsInput to StageMetrics.

        Args:
            input_data: Stage metrics input from service layer

        Returns:
            StageMetrics model for repository
        """
        return StageMetrics(
            status=input_data.status,
            jobs_processed=input_data.jobs_processed,
            jobs_completed=input_data.jobs_completed,
            jobs_failed=input_data.jobs_failed,
            execution_seconds=input_data.execution_seconds,
            started_at=input_data.started_at,
            completed_at=input_data.completed_at,
            error_message=input_data.error_message,
        )

    @staticmethod
    def summary_input_to_company_metrics(
        input_data: CompanySummaryInput,
        date: str,
        company_name: str,
    ) -> CompanyDailyMetrics:
        """Convert CompanySummaryInput to CompanyDailyMetrics.

        Args:
            input_data: Company summary input from service layer
            date: Date in YYYY-MM-DD format
            company_name: Company name

        Returns:
            CompanyDailyMetrics model for repository
        """
        return CompanyDailyMetrics(
            date=date,
            company_name=company_name,
            new_jobs_found=input_data.new_jobs_found,
            total_active_jobs=input_data.total_active_jobs,
            total_inactive_jobs=input_data.total_inactive_jobs,
            jobs_deactivated_today=input_data.jobs_deactivated_today,
            overall_status=input_data.overall_status,
            prefect_flow_run_id=input_data.prefect_flow_run_id,
            pipeline_version=input_data.pipeline_version,
        )
