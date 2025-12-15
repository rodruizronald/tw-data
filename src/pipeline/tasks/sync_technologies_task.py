"""Task for synchronizing technologies with the backend."""

from prefect import get_run_logger, task

from core.models.jobs import TechData
from data.supebase.exceptions import SupabaseConflictError

# Add this import for the Technology type
from data.supebase.models.technology import Technology
from services.supabase_service import SupabaseService


def _create_or_fetch_technology(
    service: SupabaseService,
    tech_name: str,
    parent_name: str | None,
    technology_map: dict[str, Technology],
    logger,
) -> tuple[Technology | None, str]:
    """
    Create a new technology or fetch it if it already exists.

    Args:
        service: SupabaseService instance
        tech_name: Name of the technology to create or fetch
        parent_name: Name of the parent technology (optional)
        technology_map: Map of technology names to Technology objects
        logger: Logger instance for logging

    Returns:
        Tuple of (technology object or None, status string)
        Status can be: "created", "existing", or "error"
    """
    try:
        # Resolve parent_id if parent_name is provided
        parent_id = None
        if parent_name:
            # Check if parent exists in map first
            if parent_name.lower() in technology_map:
                parent_id = technology_map[parent_name.lower()].id
            else:
                # Try to fetch parent from backend
                try:
                    parent_tech = service.get_technology_by_name(name=parent_name)
                    technology_map[parent_name.lower()] = parent_tech
                    parent_id = parent_tech.id
                except Exception as parent_error:
                    logger.warning(
                        f"Could not find parent '{parent_name}' for '{tech_name}': {parent_error}"
                    )
                    # Continue without parent - will be set in second pass if needed

        # Create technology with parent_id
        technology = service.create_technology(name=tech_name, parent_id=parent_id)
        return technology, "created"

    except SupabaseConflictError:
        try:
            technology = service.get_technology_by_name(name=tech_name)
            return technology, "existing"

        except Exception as fetch_error:
            logger.warning(
                f"Could not fetch existing technology '{tech_name}': {fetch_error}"
            )
            return None, "error"

    except Exception as create_error:
        logger.warning(f"Error creating technology '{tech_name}': {create_error}")
        return None, "error"


def _process_technology_aliases(
    service: SupabaseService,
    technology: Technology,
    tech_name: str,
    aliases: list[str],
    logger,
) -> tuple[int, int]:
    """
    Process and create aliases for a technology.

    Args:
        service: SupabaseService instance
        technology: Technology object with an 'id' attribute
        tech_name: Name of the technology (for logging)
        aliases: List of alias names to create
        logger: Logger instance for logging

    Returns:
        Tuple of (aliases_created, aliases_skipped)
    """
    aliases_created = 0
    aliases_skipped = 0

    for alias_name in aliases:
        try:
            service.create_technology_alias(
                technology_id=technology.id, alias=alias_name
            )
            aliases_created += 1

        except SupabaseConflictError:
            logger.warning(f"Skipping duplicate alias '{alias_name}' for '{tech_name}'")
            aliases_skipped += 1

        except Exception as alias_error:
            logger.warning(
                f"Error creating alias '{alias_name}' for '{tech_name}': {alias_error}"
            )

    return aliases_created, aliases_skipped


@task(
    name="sync_technologies",
    description="Synchronize technologies from source with backend",
    retries=2,
    retry_delay_seconds=10,
    timeout_seconds=1200,
    task_run_name="sync_technologies",
)
def sync_technologies_task(technologies_from_source: list[TechData]):
    """
    Synchronize technologies with the backend.
    """
    logger = get_run_logger()
    logger.info(
        f"Starting technology sync with {len(technologies_from_source)} technologies"
    )

    stats = {
        "created": 0,
        "existing": 0,
        "aliases_created": 0,
        "aliases_skipped": 0,
    }
    try:
        service = SupabaseService()

        # Fetch all existing technology names from backend
        logger.info("Fetching existing technology names from backend...")
        existing_tech_names = service.get_all_technology_names()
        existing_tech_names_set = {name.lower() for name in existing_tech_names}

        # Filter out technologies that already exist
        new_technologies = [
            tech
            for tech in technologies_from_source
            if tech.name.lower() not in existing_tech_names_set
        ]
        stats["existing"] = len(technologies_from_source) - len(new_technologies)

        logger.info(
            f"Filtered to {len(new_technologies)} new technologies "
            f"(skipped {len(technologies_from_source) - len(new_technologies)} existing)"
        )

        # Create an in-memory map to store technology records for quick lookup
        technology_map: dict[str, Technology] = {}

        for tech_data in new_technologies:
            tech_name = tech_data.name

            # Create or fetch the technology
            technology, status = _create_or_fetch_technology(
                service, tech_name, tech_data.parent, technology_map, logger
            )

            if technology is None:
                continue  # Skip this technology if there was an error

            stats[status] += 1

            # Process aliases for this technology
            if tech_data.alias:
                created, skipped = _process_technology_aliases(
                    service, technology, tech_name, tech_data.alias, logger
                )
                stats["aliases_created"] += created
                stats["aliases_skipped"] += skipped

        # Completion
        logger.info(
            f"Technology sync completed - "
            f"Created: {stats['created']}, "
            f"Existing: {stats['existing']}, "
            f"Aliases Created: {stats['aliases_created']}, "
            f"Aliases Skipped: {stats['aliases_skipped']}"
        )

    except Exception as e:
        logger.error(f"Error during technology sync: {e}")
        raise
