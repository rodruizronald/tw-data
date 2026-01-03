import asyncio

from prefect import flow, get_run_logger

from core.models.jobs import CompanyData, Job
from core.models.results import TaskResult
from pipeline.config import PipelineConfig
from pipeline.tasks.stage_3_task import process_job_skills_task
from services.data_service import JobDataService


@flow(
    name="stage_3_skills_extraction",
    description="Extract skills and responsibilities from job postings",
    version="1.0.0",
    retries=0,
    retry_delay_seconds=60,
    timeout_seconds=None,
)
async def stage_3_flow(
    companies: list[CompanyData],
    config: PipelineConfig,
) -> dict[str, list[Job]]:
    """
    Main flow for Stage 3: Extract skills and responsibilities from job postings.

    This flow orchestrates the processing of multiple companies concurrently,
    with proper error handling, validation, and result aggregation.

    Args:
        companies: List of companies to process
        config: Pipeline configuration

    Returns:
        Aggregated results from all company processing (only successful results)
    """
    logger = get_run_logger()
    logger.info("Stage 3: Skills and Responsibilities Extraction")

    db_service = JobDataService()

    # Filter enabled companies
    enabled_companies = [company for company in companies if company.enabled]

    if not enabled_companies:
        logger.warning("No enabled companies found to process")
        return {}

    logger.info(f"Processing {len(enabled_companies)} enabled companies")

    async def process_with_semaphore(
        company: CompanyData, semaphore: asyncio.Semaphore
    ) -> TaskResult[list[Job]]:
        """Process a company with semaphore to limit concurrency."""
        async with semaphore:
            try:
                jobs_data = db_service.load_jobs_for_stage(
                    company.name, config.stage_3.tag
                )

                if not jobs_data:
                    logger.info(f"No jobs data found for {company.name}")
                    return TaskResult.ok([], company.name)

                result = await process_job_skills_task(company, jobs_data, config)
                return TaskResult.ok(result, company.name)
            except Exception as e:
                logger.error(f"Task failed for {company.name}: {e}")
                return TaskResult.fail(str(e), company.name)

    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(3)

    # Create tasks for all companies
    tasks = [
        process_with_semaphore(company, semaphore) for company in enabled_companies
    ]

    # Run all tasks concurrently (limited by semaphore)
    results: list[TaskResult[list[Job]]] = await asyncio.gather(*tasks)

    # Separate successful and failed results
    successful = [r for r in results if r.is_success]
    failed = [r for r in results if r.is_failure]

    # Log summary
    logger.info(
        f"Stage 3 completed: {len(successful)} successful, {len(failed)} failed"
    )
    for failure in failed:
        logger.warning(f"  Failed: {failure.company_name} - {failure.error}")

    # Build results map from successful results only
    results_map = {r.company_name: r.data or [] for r in successful}

    return results_map
