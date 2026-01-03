import asyncio

from prefect import flow, get_run_logger

from core.models.jobs import CompanyData, Job
from pipeline.config import PipelineConfig
from pipeline.tasks.stage_1_task import (
    process_job_listings_task,
)

MAX_CONCURRENT_TASKS = 3


@flow(
    name="stage_1_job_listing_extraction",
    description="Extract job listings from company career pages with concurrent processing",
    version="1.0.0",
    retries=0,
    retry_delay_seconds=60,
    timeout_seconds=None,
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

    # Process companies in batches to limit concurrency
    results_map: dict[str, list[Job]] = {}

    for i in range(0, len(enabled_companies), MAX_CONCURRENT_TASKS):
        batch = enabled_companies[i : i + MAX_CONCURRENT_TASKS]
        logger.info(
            f"Processing batch {i // MAX_CONCURRENT_TASKS + 1}: {[c.name for c in batch]}"
        )

        # Run batch of tasks concurrently - tasks are tracked by Prefect
        batch_results = await asyncio.gather(
            *[process_job_listings_task(company, config) for company in batch],
            return_exceptions=True,
        )

        # Collect results from batch
        for company, result in zip(batch, batch_results, strict=True):
            if isinstance(result, BaseException):
                logger.error(f"Task failure: {company.name} - {result}")
                results_map[company.name] = []
            else:
                logger.info(f"Completed: {company.name}")
                results_map[company.name] = list(result)

    return results_map
