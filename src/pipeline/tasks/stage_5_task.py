"""
Stage 5 Task: Upload jobs to Supabase.

Prefect task for processing jobs and uploading them to Supabase database.
"""

from prefect import task
from prefect.logging import get_run_logger

from core.models.jobs import CompanyData, Job
from pipeline.config import PipelineConfig
from pipeline.stages.stage_5 import Stage5Processor
from pipeline.tasks.helpers import company_task_run_name
from utils.exceptions import (
    DatabaseOperationError,
    ValidationError,
)


@task(
    name="Upload Jobs to Supabase",
    description="Upload processed jobs to Supabase database",
    retries=2,
    retry_delay_seconds=30,
    timeout_seconds=None,
    task_run_name=company_task_run_name,  # type: ignore[arg-type]
)
def upload_jobs_to_supabase_task(
    company: CompanyData,
    jobs: list[Job],
    config: PipelineConfig,
) -> list[Job]:
    """
    Prefect task to upload jobs to Supabase for a single company.

    Args:
        company: Company data containing company information
        jobs: List of jobs to upload (completed stages 1-4)
        config: Pipeline configuration

    Returns:
        List of successfully uploaded jobs
    """
    logger = get_run_logger()

    try:
        logger.info(f"Starting Supabase upload task for company: {company.name}")

        # Initialize processor
        processor = Stage5Processor(config)

        # Process jobs (upload to Supabase)
        results: list[Job] = processor.process_jobs(jobs, company.name)

        return results

    except ValidationError as e:
        # Non-retryable errors - don't retry these
        logger.error(f"Validation error for {company.name}: {e}")
        return []

    except DatabaseOperationError as e:
        # Retryable errors - let Prefect handle retries
        logger.warning(f"Database error for {company.name}: {e}")
        # Re-raise to trigger Prefect retry mechanism
        raise

    except Exception as e:
        # Unexpected errors - log and re-raise for retry
        logger.error(f"Unexpected error for {company.name}: {e}")
        # Re-raise to trigger Prefect retry mechanism
        raise
