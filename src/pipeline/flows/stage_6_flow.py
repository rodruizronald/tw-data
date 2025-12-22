"""
Stage 6 Flow: Company Completion Metrics and Daily Aggregates.

This flow records company completion metrics for each company after all stages
have been processed, and calculates daily aggregates for the entire pipeline.
"""

from prefect import flow, get_run_logger

from core.models.jobs import CompanyData
from core.models.metrics import CompanyStatus, CompanySummaryInput
from pipeline.config import PipelineConfig
from services.data_service import JobDataService
from services.metrics_service import JobMetricsService
from utils.timezone import now_utc


@flow(
    name="stage_6_metrics_completion",
    description="Record company completion metrics and calculate daily aggregates",
    version="1.0.0",
    retries=0,
    retry_delay_seconds=60,
    timeout_seconds=600,  # 10 minutes timeout
)
async def stage_6_flow(
    companies: list[CompanyData],
    config: PipelineConfig,
) -> None:
    """
    Main flow for Stage 6: Record company completion metrics and calculate daily aggregates.

    This flow processes each company to:
    1. Gather statistics from the database
    2. Determine overall company status based on stage completion
    3. Record company completion metrics
    4. Calculate daily aggregates for the entire pipeline

    Args:
        companies: List of companies that were processed
        config: Pipeline configuration
    """
    logger = get_run_logger()
    logger.info("STAGE 6: Company Completion Metrics and Daily Aggregates")

    db_service = JobDataService()
    metrics_service = JobMetricsService()

    # Get today's date using timezone utility
    today = now_utc().strftime("%Y-%m-%d")

    # Process each company to record completion metrics
    for company in companies:
        try:
            if not company.enabled:
                continue

            logger.info(f"Recording completion metrics for {company.name}")

            # Get stage statistics for the company
            stats = db_service.get_stage_statistics(company.name)

            # Determine overall company status
            overall_status = _determine_company_status(
                company.name, today, metrics_service, config, logger
            )

            # Create summary input
            summary_input = CompanySummaryInput(
                new_jobs_found=stats.get("new_jobs", 0),
                total_active_jobs=stats.get("active_jobs", 0),
                total_inactive_jobs=stats.get("inactive_jobs", 0),
                jobs_deactivated_today=stats.get("jobs_deactivated", 0),
                overall_status=overall_status,
            )

            # Record company completion metrics
            metrics_service.record_company_completion(
                company_name=company.name,
                summary_input=summary_input,
            )

        except Exception as e:
            logger.error(f"Error recording completion for {company.name}: {e}")
            continue

    # Calculate daily aggregates for the entire pipeline
    try:
        metrics_service.calculate_daily_aggregates()
        logger.info("Daily aggregates calculated successfully")
    except Exception as e:
        logger.error(f"Error calculating daily aggregates: {e}")


def _determine_company_status(
    company_name: str,
    date: str,
    metrics_service: JobMetricsService,
    config: PipelineConfig,
    logger,
) -> CompanyStatus:
    """
    Determine the overall status of a company based on all enabled stages.

    The status is determined as follows:
    - SUCCESS: All enabled stages completed successfully
    - PARTIAL: Some stages succeeded, some failed
    - FAILED: All enabled stages failed or no stages were successful
    - PENDING: No stage metrics found

    Args:
        company_name: Name of the company
        date: Date in YYYY-MM-DD format
        metrics_service: JobMetricsService instance
        config: Pipeline configuration
        logger: Logger instance

    Returns:
        CompanyStatus enum value
    """
    try:
        # Get company metrics for the day
        metrics_list = metrics_service.get_company_metrics(company_name, date, date)

        if not metrics_list:
            logger.warning(f"No metrics found for {company_name} on {date}")
            return CompanyStatus.PENDING

        metrics = metrics_list[0]  # Get today's metrics

        # Determine which stages are enabled
        enabled_stages = _get_enabled_stages(config)

        if not enabled_stages:
            logger.warning("No stages are enabled")
            return CompanyStatus.PENDING

        # Count successful and failed stages
        successful_stages, failed_stages = _count_stage_statuses(
            metrics, enabled_stages
        )

        # Determine overall status based on stage results
        return _calculate_overall_status(
            successful_stages, failed_stages, len(enabled_stages)
        )

    except Exception as e:
        logger.error(f"Error determining status for {company_name}: {e}")
        return CompanyStatus.UNKNOWN


def _get_enabled_stages(config: PipelineConfig) -> list[int]:
    """Get list of enabled stage numbers from configuration."""
    enabled_stages = []
    if config.stage_1.enabled:
        enabled_stages.append(1)
    if config.stage_2.enabled:
        enabled_stages.append(2)
    if config.stage_3.enabled:
        enabled_stages.append(3)
    if config.stage_4.enabled:
        enabled_stages.append(4)
    return enabled_stages


def _count_stage_statuses(metrics, enabled_stages: list[int]) -> tuple[int, int]:
    """
    Count successful and failed stages.

    Returns:
        Tuple of (successful_stages, failed_stages)
    """
    successful_stages = 0
    failed_stages = 0

    for stage_num in enabled_stages:
        stage_status = getattr(metrics, f"stage_{stage_num}_status", None)

        if stage_status == "success":
            successful_stages += 1
        elif stage_status == "failed":
            failed_stages += 1
        # If status is None or "skipped", we don't count it

    return successful_stages, failed_stages


def _calculate_overall_status(
    successful_stages: int, failed_stages: int, total_enabled: int
) -> CompanyStatus:
    """
    Calculate overall company status based on stage results.

    Args:
        successful_stages: Number of successful stages
        failed_stages: Number of failed stages
        total_enabled: Total number of enabled stages

    Returns:
        CompanyStatus enum value
    """
    total_stages_with_status = successful_stages + failed_stages

    if total_stages_with_status == 0:
        # No stages have completed yet
        return CompanyStatus.PENDING

    if successful_stages == total_enabled:
        # All enabled stages succeeded
        return CompanyStatus.SUCCESS

    if failed_stages == total_enabled:
        # All enabled stages failed
        return CompanyStatus.FAILED

    # Mix of successes and failures
    return CompanyStatus.PARTIAL
