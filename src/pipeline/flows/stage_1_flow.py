from prefect import flow, get_run_logger
from prefect.futures import wait
from prefect.task_runners import ThreadPoolTaskRunner

from core.models.jobs import CompanyData, Job
from pipeline.config import PipelineConfig
from pipeline.tasks.stage_1_task import (
    process_job_listings_task,
)


@flow(
    name="stage_1_job_listing_extraction",
    description="Extract job listings from company career pages with concurrent processing",
    version="1.0.0",
    retries=0,
    retry_delay_seconds=60,
    timeout_seconds=None,
    task_runner=ThreadPoolTaskRunner(max_workers=3),  # type: ignore[arg-type]
)
async def stage_1_flow(
    companies: list[CompanyData],
    config: PipelineConfig,
) -> dict[str, list[Job]]:
    """
    Main flow for Stage 1: Extract job listings from company career pages.

    This flow orchestrates the processing of multiple companies concurrently,
    with proper error handling, validation, and result aggregation.

    Args:
        companies: List of companies to process
        config: Pipeline configuration

    Returns:
        Aggregated results from all company processing
    """
    logger = get_run_logger()
    logger.info("Stage 1: Job Listing Extraction")

    # Filter enabled companies
    enabled_companies = [company for company in companies if company.enabled]

    if not enabled_companies:
        logger.warning("No enabled companies found to process")
        return {}

    logger.info(f"Processing {len(enabled_companies)} enabled companies")

    # Submit all tasks (concurrency controlled by ThreadPoolTaskRunner)
    futures = []
    for company in enabled_companies:
        future = process_job_listings_task.submit(company, config)
        futures.append((company.name, future))

    # Wait for all tasks to complete
    wait([f for _, f in futures])

    # Collect results
    results_map = {}
    for company_name, future in futures:
        try:
            result = future.result()
            results_map[company_name] = result
            logger.info(f"Completed: {company_name}")
        except Exception as e:
            logger.error(f"Task failure: {company_name} - {e}")
            results_map[company_name] = []

    return results_map
