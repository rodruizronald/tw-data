import logging

from prefect import flow, get_run_logger

from core.models.jobs import CompanyData, Job
from pipeline.config import PipelineConfig
from pipeline.flows.helpers import (
    load_companies_from_file,
    validate_flow_inputs,
)
from pipeline.flows.stage_1_flow import stage_1_flow
from pipeline.flows.stage_2_flow import stage_2_flow
from pipeline.flows.stage_3_flow import stage_3_flow
from pipeline.flows.stage_4_flow import stage_4_flow
from pipeline.flows.stage_5_flow import stage_5_flow
from pipeline.flows.stage_6_flow import stage_6_flow
from services.data_service import JobDataService


@flow(
    name="job_processing_pipeline",
    description="Complete end-to-end job processing pipeline",
    version="1.0.0",
    retries=0,  # No retries at pipeline level - let individual stages handle retries
    timeout_seconds=14400,  # 4 hour total pipeline timeout
)
async def main_pipeline_flow() -> None:
    """
    Main pipeline flow that orchestrates all stages of job processing.

    This flow runs the complete pipeline from job extraction to final analysis:
    - Stage 1: Extract job listings from company career pages
    - Stage 2: Extract detailed job descriptions
    - Stage 3: Extract skills and responsibilities
    - Stage 4: Extract technologies and tools
    - Stage 5: Record company completion metrics and calculate daily aggregates

    Returns:
        Complete pipeline execution results
    """
    logger = get_run_logger()
    logger.info("Starting Job Processing Pipeline")

    try:
        # Load configuration
        config = PipelineConfig.load()
        logger.info("Configuration loaded")

        # Check if pipeline is enabled
        if not config.enabled:
            logger.warning("Pipeline is disabled in configuration - skipping execution")
            return

        logger.info("Configuring service loggers...")
        # Just set the levels - don't touch handlers or formatters
        for logger_name in [
            "services.data_service",
            "services.openai_service",
            "services.web_extraction_service",
            "services.metrics_service",
        ]:
            logging.getLogger(logger_name).setLevel(logging.INFO)

        # Initialize paths
        config.initialize_paths()
        logger.info("Paths initialized")

        # Load companies
        companies = load_companies_from_file(config.companies_file_path, logger)
        logger.info(f"Loaded {len(companies)} companies")

        # Parse stages
        stages_to_run = config.stages.get_enabled_stage_tags()
        logger.info(f"Stages to run: {', '.join(stages_to_run)}")

        validate_flow_inputs(companies, config)
        logger.info("Input validation passed")

        # Clean up incomplete jobs before starting pipeline
        logger.info("Cleaning up incomplete jobs from previous runs...")
        data_service = JobDataService()
        total_removed = 0

        for company in companies:
            try:
                removed_count = data_service.remove_incomplete_jobs(company.name)
                total_removed += removed_count
            except Exception as e:
                logger.warning(
                    f"Failed to remove incomplete jobs for {company.name}: {e}"
                )

        logger.info(f"Removed {total_removed} incomplete jobs across all companies")

        # Run pipeline
        logger.info("Starting pipeline execution...")

        # Execute stages
        await _execute_stages(
            config,
            companies,
            logger,
        )

        logger.info("Pipeline execution completed!")
    except Exception as e:
        # Pipeline-level failure
        logger.error(f"Pipeline failed: {e}")
        raise


async def _execute_stages(
    config: PipelineConfig,
    companies: list[CompanyData],
    logger,
) -> None:
    """Execute all requested pipeline stages."""

    # Stage 1: Job Listing Extraction
    if config.stage_1.enabled:
        await _execute_stage_1(
            config,
            companies,
            logger,
        )

    # Stage 2: Job Listing Extraction
    if config.stage_2.enabled:
        await _execute_stage_2(
            config,
            companies,
            logger,
        )

    # Stage 3: Skills and Responsibilities Extraction
    if config.stage_3.enabled:
        await _execute_stage_3(
            config,
            companies,
            logger,
        )

    # Stage 4: Technologies and Tools Extraction
    if config.stage_4.enabled:
        await _execute_stage_4(
            config,
            companies,
            logger,
        )

    # Stage 5: Supabase Upload
    if config.stage_5.enabled:
        await _execute_stage_5(
            config,
            companies,
            logger,
        )

    # Stage 6: Company Completion Metrics and Daily Aggregates
    await _execute_stage_6(
        config,
        companies,
        logger,
    )


async def _execute_stage_1(
    config: PipelineConfig,
    companies: list[CompanyData],
    logger,
) -> dict[str, list[Job]]:
    """Execute Stage 1: Job Listing Extraction."""
    logger.info("Stage 1 starting...")

    try:
        results: dict[str, list[Job]] = await stage_1_flow(
            companies=companies,
            config=config,
        )

        logger.info("Stage 1 completed successfully")
        return results

    except Exception as e:
        logger.error(f"Stage 1 failed: {e}")

        logger.error("Critical failure in Stage 1 - stopping pipeline")
        raise


async def _execute_stage_2(
    config: PipelineConfig,
    companies: list[CompanyData],
    logger,
) -> dict[str, list[Job]]:
    """Execute Stage 2: Job Details Extraction."""
    logger.info("Stage 2 starting...")

    try:
        results: dict[str, list[Job]] = await stage_2_flow(
            companies=companies,
            config=config,
        )

        logger.info("Stage 2 completed successfully")
        return results

    except Exception as e:
        logger.error(f"Stage 2 failed: {e}")

        logger.error("Critical failure in Stage 2 - stopping pipeline")
        raise


async def _execute_stage_3(
    config: PipelineConfig,
    companies: list[CompanyData],
    logger,
) -> dict[str, list[Job]]:
    """Execute Stage 3: Skills and Responsibilities Extraction."""
    logger.info("Stage 3 starting...")

    try:
        results: dict[str, list[Job]] = await stage_3_flow(
            companies=companies,
            config=config,
        )

        logger.info("Stage 3 completed successfully")
        return results

    except Exception as e:
        logger.error(f"Stage 3 failed: {e}")

        logger.error("Critical failure in Stage 3 - stopping pipeline")
        raise


async def _execute_stage_4(
    config: PipelineConfig,
    companies: list[CompanyData],
    logger,
) -> None:
    """Execute Stage 4: Technologies and Tools Extraction."""
    logger.info("Stage 4 starting...")

    try:
        await stage_4_flow(
            companies=companies,
            config=config,
        )

        logger.info("Stage 4 completed successfully")

    except Exception as e:
        logger.error(f"Stage 4 failed: {e}")

        logger.error("Critical failure in Stage 4 - stopping pipeline")
        raise


async def _execute_stage_5(
    config: PipelineConfig,
    companies: list[CompanyData],
    logger,
) -> None:
    """Execute Stage 5: Supabase Upload."""
    logger.info("Stage 5 starting...")

    try:
        await stage_5_flow(
            companies=companies,
            config=config,
        )

        logger.info("Stage 5 completed successfully")

    except Exception as e:
        logger.error(f"Stage 5 failed: {e}")

        logger.error("Critical failure in Stage 5 - stopping pipeline")
        raise


async def _execute_stage_6(
    config: PipelineConfig,
    companies: list[CompanyData],
    logger,
) -> None:
    """Execute Stage 6: Company Completion Metrics and Daily Aggregates."""
    logger.info("Stage 6 starting...")

    try:
        await stage_6_flow(
            companies=companies,
            config=config,
        )

        logger.info("Stage 6 completed successfully")

    except Exception as e:
        logger.error(f"Stage 6 failed: {e}")
        # Don't raise - we don't want metrics recording failure to stop the pipeline
        logger.warning("Stage 6 failed but pipeline will continue")
