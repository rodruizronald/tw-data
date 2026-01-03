import asyncio

from prefect import flow, get_run_logger

from core.models.jobs import CompanyData, Job
from pipeline.config import PipelineConfig
from pipeline.tasks.stage_4_task import process_job_technologies_task
from services.data_service import JobDataService


@flow(
    name="stage_4_technologies_extraction",
    description="Extract technologies and tools from job postings",
    version="1.0.0",
    retries=0,
    retry_delay_seconds=60,
    timeout_seconds=None,
)
async def stage_4_flow(
    companies: list[CompanyData],
    config: PipelineConfig,
) -> dict[str, list[Job]]:
    """
    Main flow for Stage 4: Extract technologies and tools from job postings.

    This flow orchestrates the processing of multiple companies concurrently,
    with proper error handling, validation, and result aggregation.

    Args:
        companies: List of companies to process
        config: Pipeline configuration
        stage_3_results: Results from stage 3 or None to load from database
    """
    logger = get_run_logger()
    logger.info("STAGE 4: Technologies and Tools Extraction")

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
                jobs_data = db_service.load_jobs_for_stage(
                    company.name, config.stage_4.tag
                )

                if not jobs_data:
                    logger.info(f"No jobs data found for {company.name}")
                    return company.name, []

                result = await process_job_technologies_task(company, jobs_data, config)
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
