"""Flow to synchronize companies and technologies with the backend."""

import logging

from prefect import flow, get_run_logger

from pipeline.config import PipelineConfig
from pipeline.flows.helpers import load_companies_from_file
from pipeline.tasks.sync_companies_task import sync_companies_task


@flow(
    name="sync_backend",
    description="Synchronize companies and technologies with the backend",
    version="1.0.0",
    retries=0,
    timeout_seconds=300,  # 5 minute timeout
)
async def sync_backend_flow():
    """
    Synchronize backend data before running the main pipeline.

    This flow ensures that all companies and technologies from the configuration
    files exist in the backend database before processing jobs.

    Steps:
    1. Load companies from companies.yaml
    2. Fetch existing companies from backend
    3. Create missing companies
    4. (Future) Sync job technologies

    Returns:
        Dictionary with sync statistics for companies and technologies
    """
    logger = get_run_logger()
    logger.info("Starting backend synchronization flow")

    try:
        # Load configuration
        config = PipelineConfig.load()
        logger.info("Configuration loaded")

        # Configure service loggers
        logger.info("Configuring service loggers...")
        logging.getLogger("services.company_service").setLevel(logging.INFO)

        # Load companies from YAML file
        logger.info(f"Loading companies from: {config.companies_file_path}")
        companies = load_companies_from_file(config.companies_file_path, logger)

        # Sync companies with backend
        company_stats = sync_companies_task(companies)

        # Prepare results
        results = {
            "companies": company_stats,
            # "technologies": {}  # To be implemented later
        }

        logger.info("Backend synchronization completed successfully")
        logger.info(f"Summary: {results}")

    except Exception as e:
        logger.error(f"Backend synchronization failed: {e}")
        raise
