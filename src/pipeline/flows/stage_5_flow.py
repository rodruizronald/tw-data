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

    async def process_with_semaphore(
        company: CompanyData, semaphore: asyncio.Semaphore
    ) -> tuple[str, list[Job]]:
        """Process a company with semaphore to limit concurrency."""
        async with semaphore:
            try:
                # Load jobs ready for stage 5 (completed stages 1-4)
                jobs_data = db_service.load_jobs_for_stage(
                    company.name, config.stage_5.tag
                )

                if not jobs_data:
                    logger.info(f"No jobs ready for Supabase upload for {company.name}")
                    return company.name, []

                # Run the synchronous task
                result = upload_jobs_to_supabase_task(company, jobs_data, config)
                logger.info(f"Completed: {company.name}")
                return company.name, result
            except Exception as e:
                logger.error(f"Unexpected task failure: {company.name} - {e}")
                return company.name, []

    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(3)

    # Create tasks for all companies
    tasks = [
        process_with_semaphore(company, semaphore) for company in enabled_companies
    ]

    # Run all tasks concurrently (limited by semaphore)
    results = await asyncio.gather(*tasks)

    # Build results map
    results_map = dict(results)

    return results_map
