from prefect import task
from prefect.logging import get_run_logger

from core.models.jobs import CompanyData, Job
from pipeline.config import PipelineConfig
from pipeline.stages.stage_1 import Stage1Processor
from pipeline.tasks.helpers import company_task_run_name
from utils.exceptions import PipelineError


@task(
    name="Process Company",
    description="Extract job listings from a single company's career page",
    retries=0,
    retry_delay_seconds=30,
    timeout_seconds=None,
    task_run_name=company_task_run_name,  # type: ignore[arg-type]
)
async def process_job_listings_task(
    company: CompanyData,
    config: PipelineConfig,
) -> list[Job]:
    """
    Prefect task to process a single company for job listings.

    Args:
        company: Company data containing configuration
        config: Pipeline configuration

    Returns:
        List of extracted jobs, empty list on non-retryable errors

    Raises:
        PipelineError: For retryable errors (triggers Prefect retry)
        Exception: For unexpected errors (triggers Prefect retry)
    """
    logger = get_run_logger()
    logger.info(f"Starting task for company: {company.name}")

    processor = Stage1Processor(config)

    try:
        results: list[Job] = await processor.process_single_company(company)
        return results
    except PipelineError as e:
        if e.retryable:
            # Retryable errors - let Prefect handle retries
            raise
        # Non-retryable errors - log and return empty
        logger.error(f"Non-retryable error for {company.name}: {e}")
        return []
    except Exception as e:
        # Unexpected errors - log and re-raise for retry
        logger.error(f"Unexpected error for {company.name}: {e}")
        raise
