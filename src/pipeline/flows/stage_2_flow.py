import asyncio

from prefect import flow, get_run_logger

from core.models.jobs import CompanyData, Job
from pipeline.config import PipelineConfig
from pipeline.tasks.stage_2_task import process_job_details_task
from services.data_service import JobDataService

MAX_CONCURRENT_TASKS = 3


@flow(
    name="stage_2_job_details_extraction",
    description="Extract job eligibility, metadata, and detailed descriptions from individual job postings",
    version="1.0.0",
    retries=0,
    retry_delay_seconds=60,
    timeout_seconds=None,
)
async def stage_2_flow(
    companies: list[CompanyData],
    config: PipelineConfig,
) -> dict[str, list[Job]]:
    """
    Main flow for Stage 2: Extract job eligibility, metadata, and detailed descriptions from individual job postings.

    This flow orchestrates the processing of multiple companies concurrently,
    with proper error handling, validation, and result aggregation.

    Args:
        companies: List of companies to process
        config: Pipeline configuration
        stage_1_results: Results from stage 1 or None to load from database
    """
    logger = get_run_logger()
    logger.info("Stage 2: Job Details Extraction")

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
        jobs_data = db_service.load_jobs_for_stage(company.name, config.stage_2.tag)
        if not jobs_data:
            logger.info(f"No jobs data found for {company.name}")
            continue
        companies_with_jobs.append((company, jobs_data))

    # Process companies in batches to limit concurrency
    results_map: dict[str, list[Job]] = {}

    for i in range(0, len(companies_with_jobs), MAX_CONCURRENT_TASKS):
        batch = companies_with_jobs[i : i + MAX_CONCURRENT_TASKS]
        logger.info(
            f"Processing batch {i // MAX_CONCURRENT_TASKS + 1}: {[c.name for c, _ in batch]}"
        )

        # Run batch of tasks concurrently - tasks are tracked by Prefect
        batch_results = await asyncio.gather(
            *[
                process_job_details_task(company, jobs_data, config)
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
