from prefect import task
from prefect.logging import get_run_logger

from core.models.jobs import CompanyData, Job
from pipeline.config import PipelineConfig
from pipeline.stages.stage_2 import Stage2Processor
from pipeline.tasks.helpers import company_task_run_name
from utils.exceptions import PipelineError


@task(
    name="Process Job",
    description="Extract eligibility and metadata from a single job posting",
    retries=0,
    retry_delay_seconds=30,
    timeout_seconds=None,
    task_run_name=company_task_run_name,  # type: ignore[arg-type]
)
async def process_job_details_task(
    company: CompanyData,
    jobs: list[Job],
    config: PipelineConfig,
) -> list[Job]:
    """
    Prefect task to process jobs for eligibility analysis.

    Args:
        company: Company data containing configuration
        jobs: Job objects from Stage 1
        config: Pipeline configuration

    Returns:
        List of processed jobs, empty list on non-retryable errors

    Raises:
        PipelineError: For retryable errors (triggers Prefect retry)
        Exception: For unexpected errors (triggers Prefect retry)
    """
    logger = get_run_logger()
    logger.info(f"Starting task for company: {company.name}")

    processor = Stage2Processor(config, company.web_parser_config)

    try:
        results: list[Job] = await processor.process_jobs(jobs, company.name)
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
