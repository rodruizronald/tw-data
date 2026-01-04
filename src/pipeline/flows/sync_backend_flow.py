"""Flow to synchronize companies with the backend."""

import logging

from prefect import flow, get_run_logger

from pipeline.config import PipelineConfig
from pipeline.flows.helpers import load_companies_from_file, load_technologies_from_file
from pipeline.tasks.sync_companies_task import sync_companies_task
from pipeline.tasks.sync_technologies_task import sync_technologies_task


@flow(
    name="sync_backend",
    description="Synchronize companies with the backend database",
    version="1.0.0",
    retries=0,
    timeout_seconds=3600,
)
async def sync_backend_flow():
    """
    Synchronize backend data before running the main pipeline.

    This flow ensures that all companies and technologies from the configuration files exist
    in the backend database with the correct activation status before processing jobs.

    Steps:
    1. Load companies from companies.yaml
    2. Fetch existing companies from backend (all companies, active and inactive)
    3. Create missing companies with correct activation status
    4. Activate companies that are enabled in YAML but inactive in backend
    5. Deactivate companies that are disabled in YAML but active in backend
    6. Load technologies from technologies.json
    7. Sync technologies with backend (create missing technologies and aliases)
    """
    logger = get_run_logger()
    logger.info("Starting backend synchronization flow")

    try:
        # Load configuration
        config = PipelineConfig.load()
        logger.info("Configuration loaded")

        # Configure service loggers
        logger.info("Configuring service loggers...")
        logging.getLogger("services.supabase_service").setLevel(logging.INFO)

        # Load companies from YAML file
        logger.info(f"Loading companies from: {config.companies_file_path}")
        companies = load_companies_from_file(config.companies_file_path, logger)

        # Sync companies with backend
        sync_companies_task(companies)

        # Load technologies from JSON file
        logger.info(f"Loading technologies from: {config.paths.technologies_file}")
        technologies = load_technologies_from_file(
            config.paths.technologies_file, logger
        )

        # Separate parent and non-parent technologies
        parent_technologies = [tech for tech in technologies if tech.is_parent]
        child_technologies = [tech for tech in technologies if not tech.is_parent]

        logger.info(
            f"Found {len(parent_technologies)} parent technologies and "
            f"{len(child_technologies)} child technologies"
        )

        # First sync parent technologies to ensure they exist before children reference them
        logger.info("Syncing parent technologies...")
        sync_technologies_task(parent_technologies)

        # Then sync child technologies (non-parents)
        logger.info("Syncing child technologies...")
        sync_technologies_task(child_technologies)

    except Exception as e:
        logger.error(f"Backend synchronization failed: {e}")
        raise
