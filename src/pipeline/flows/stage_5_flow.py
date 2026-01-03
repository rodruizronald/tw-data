"""
Stage 5 Flow: Upload jobs to Supabase.

This flow orchestrates the upload of processed jobs to Supabase database
for all enabled companies.
"""

import asyncio

from prefect import flow, get_run_logger

from core.models.jobs import CompanyData, Job
from pipeline.config import PipelineConfig
from pipeline.tasks.stage_5_task import upload_jobs_to_supabase_task
from services.data_service import JobDataService

MAX_CONCURRENT_TASKS = 3


@flow(
    name="stage_5_supabase_upload",
    description="Upload processed jobs to Supabase database",
    version="1.0.0",
    retries=0,
    retry_delay_seconds=60,
    timeout_seconds=None,
)
async def stage_5_flow(
    companies: list[CompanyData],
    config: PipelineConfig,
) -> dict[str, list[Job]]:
    """
    Main flow for Stage 5: Upload jobs to Supabase.

    This flow orchestrates the upload of jobs that have completed stages 1-4
    to Supabase database. It processes multiple companies concurrently with
    proper error handling and result aggregation.

    Args:
        companies: List of companies to process
        config: Pipeline configuration

    Returns:
        Dictionary mapping company names to lists of successfully uploaded jobs
    """
    logger = get_run_logger()
    logger.info("STAGE 5: Supabase Upload")

    db_service = JobDataService()

    # Filter enabled companies
    enabled_companies = [company for company in companies if company.enabled]

    if not enabled_companies:
        logger.warning("No enabled companies found to process")
        return {}

    logger.info(f"Processing {len(enabled_companies)} enabled companies")

    # Prepare companies with their jobs data
    companies_with_jobs: list[tuple[CompanyData, list[Job]]] = []
    for company in enabled_companies:
        # Load jobs ready for stage 5 (completed stages 1-4)
        jobs_data = db_service.load_jobs_for_stage(company.name, config.stage_5.tag)
        if not jobs_data:
            logger.info(f"No jobs ready for Supabase upload for {company.name}")
            continue
        companies_with_jobs.append((company, jobs_data))

    # Process companies in batches to limit concurrency
    results_map: dict[str, list[Job]] = {}

    for i in range(0, len(companies_with_jobs), MAX_CONCURRENT_TASKS):
        batch = companies_with_jobs[i : i + MAX_CONCURRENT_TASKS]
        logger.info(
            f"Processing batch {i // MAX_CONCURRENT_TASKS + 1}: {[c.name for c, _ in batch]}"
        )

        # Run batch of sync tasks concurrently using asyncio.to_thread
        batch_results = await asyncio.gather(
            *[
                asyncio.to_thread(
                    upload_jobs_to_supabase_task, company, jobs_data, config
                )
                for company, jobs_data in batch
            ],
            return_exceptions=True,
        )

        # Collect results from batch
        for (company, _), result in zip(batch, batch_results, strict=True):
            if isinstance(result, BaseException):
                logger.error(f"Task failure: {company.name} - {result}")
                results_map[company.name] = []
            else:
                logger.info(f"Completed: {company.name}")
                results_map[company.name] = list(result)

    return results_map
