"""Flow to synchronize companies with the backend."""

import logging

from prefect import flow, get_run_logger

from pipeline.config import PipelineConfig
from pipeline.flows.helpers import load_companies_from_file
from pipeline.tasks.sync_companies_task import sync_companies_task


@flow(
    name="sync_backend",
    description="Synchronize companies with the backend database",
    version="1.0.0",
    retries=0,
    timeout_seconds=300,  # 5 minute timeout
)
async def sync_backend_flow() -> dict[str, dict[str, int]]:
    """
    Synchronize backend data before running the main pipeline.

    This flow ensures that all companies from the configuration file exist
    in the backend database with the correct activation status before processing jobs.

    Steps:
    1. Load companies from companies.yaml
    2. Fetch existing companies from backend (all companies, active and inactive)
    3. Create missing companies with correct activation status
    4. Activate companies that are enabled in YAML but inactive in backend
    5. Deactivate companies that are disabled in YAML but active in backend

    Returns:
        Dictionary with sync statistics for companies:
        {
            "companies": {
                "total_yaml": int,
                "total_backend": int,
                "created": int,
                "activated": int,
                "deactivated": int,
                "already_synced": int
            }
        }
    """
    logger = get_run_logger()
    logger.info("Starting backend synchronization flow")

    try:
        # Load configuration
        config = PipelineConfig.load()
        logger.info("Configuration loaded")

        # Configure service loggers
        logger.info("Configuring service loggers...")
        logging.getLogger("services.supabase_data_service").setLevel(logging.INFO)
        logging.getLogger("data.supebase.repositories.companies").setLevel(logging.INFO)

        # Load companies from YAML file
        logger.info(f"Loading companies from: {config.companies_file_path}")
        companies = load_companies_from_file(config.companies_file_path, logger)

        # Sync companies with backend
        company_stats = sync_companies_task(companies)

        # Prepare results
        results = {
            "companies": company_stats,
        }

        logger.info("Backend synchronization completed successfully")
        logger.info(f"Summary: {results}")

        return results

    except Exception as e:
        logger.error(f"Backend synchronization failed: {e}")
        raise
