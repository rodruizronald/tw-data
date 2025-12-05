"""Task for synchronizing technologies with the backend."""

from prefect import get_run_logger, task

from core.models.jobs import TechData
from data.supebase.exceptions import SupabaseConflictError

# Add this import for the Technology type
from data.supebase.models.technology import Technology
from services.supabase_service import SupabaseService


def _create_or_fetch_technology(
    service: SupabaseService, tech_name: str, logger
) -> tuple[Technology | None, str]:
    """
    Create a new technology or fetch it if it already exists.

    Args:
        service: SupabaseService instance
        tech_name: Name of the technology to create or fetch
        logger: Logger instance for logging

    Returns:
        Tuple of (technology object or None, status string)
        Status can be: "created", "existing", or "error"
    """
    try:
        logger.info(f"Creating technology: {tech_name}")
        technology = service.create_technology(name=tech_name, parent_id=None)
        logger.info(
            f"Successfully created technology '{tech_name}' with ID: {technology.id}"
        )
        return technology, "created"

    except SupabaseConflictError:
        logger.info(f"Technology '{tech_name}' already exists, fetching it...")

        try:
            technology = service.get_technology_by_name(name=tech_name)
            logger.info(
                f"Successfully fetched existing technology '{tech_name}' with ID: {technology.id}"
            )
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
    logger.info(f"Processing {len(aliases)} aliases for '{tech_name}'...")

    for alias_name in aliases:
        try:
            service.create_technology_alias(
                technology_id=technology.id, alias=alias_name
            )
            logger.info(f"Successfully created alias '{alias_name}' for '{tech_name}'")
            aliases_created += 1

        except SupabaseConflictError:
            logger.info(f"Skipping duplicate alias '{alias_name}' for '{tech_name}'")
            aliases_skipped += 1

        except Exception as alias_error:
            logger.warning(
                f"Error creating alias '{alias_name}' for '{tech_name}': {alias_error}"
            )

    return aliases_created, aliases_skipped


def _update_parent_relationship(
    service: SupabaseService,
    tech_name: str,
    parent_name: str,
    technology_map: dict[str, Technology],
    logger,
) -> bool:
    """
    Update parent relationship for a technology.

    Args:
        service: SupabaseService instance
        tech_name: Name of the technology to update
        parent_name: Name of the parent technology
        technology_map: Map of technology names (lowercase) to technology objects
        logger: Logger instance for logging

    Returns:
        True if parent was successfully updated, False otherwise
    """

    if tech_name.lower() not in technology_map:
        logger.warning(
            f"Cannot update parent for '{tech_name}': technology not found in map"
        )

        return False

    if parent_name.lower() not in technology_map:
        logger.warning(
            f"Cannot find parent '{parent_name}' for technology '{tech_name}'"
        )

        return False

    try:
        current_technology = technology_map[tech_name.lower()]
        parent_technology = technology_map[parent_name.lower()]
        service.update_technology(
            technology_id=current_technology.id,
            parent_id=parent_technology.id,
        )

        logger.info(
            f"Successfully set parent of '{tech_name}' to '{parent_name}' "
            f"(parent_id={parent_technology.id})"
        )

        return True

    except Exception as update_error:
        logger.warning(f"Error updating parent for '{tech_name}': {update_error}")

        return False


@task(
    name="sync_technologies",
    description="Synchronize technologies from source with backend",
    retries=2,
    retry_delay_seconds=10,
    timeout_seconds=60,
    task_run_name="sync_technologies",
)
def sync_technologies_task(technologies_from_source: list[TechData]):
    """
    Synchronize technologies with the backend.

    This task performs a two-pass synchronization:
    - First pass: Creates technologies (without parent references) and their aliases
    - Second pass: Updates parent relationships between technologies

    The two-pass approach ensures all technologies exist before establishing
    hierarchical relationships, handling cases where child technologies appear
    before their parents in the source data.

    Args:
        technologies_from_source: List of technologies to synchronize
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
        "parents_updated": 0,
    }
    try:
        service = SupabaseService()

        # Fetch all existing technology names from backend
        logger.info("Fetching existing technology names from backend...")
        existing_tech_names = service.get_all_technology_names()
        existing_tech_names_set = {name.lower() for name in existing_tech_names}

        logger.info(f"Found {len(existing_tech_names_set)} existing technologies")

        # Filter out technologies that already exist
        new_technologies = [
            tech
            for tech in technologies_from_source
            if tech.name.lower() not in existing_tech_names_set
        ]

        logger.info(
            f"Filtered to {len(new_technologies)} new technologies "
            f"(skipped {len(technologies_from_source) - len(new_technologies)} existing)"
        )

        # Create an in-memory map to store technology records for quick lookup
        technology_map: dict[str, Technology] = {}

        # =================================================================
        # FIRST PASS: Create technologies and their aliases
        # =================================================================
        logger.info("Starting first pass: Creating technologies and aliases...")

        for tech_data in new_technologies:
            tech_name = tech_data.name

            # Create or fetch the technology
            technology, status = _create_or_fetch_technology(service, tech_name, logger)

            if technology is None:
                continue  # Skip this technology if there was an error

            # Update technology map and stats
            technology_map[tech_name.lower()] = technology
            stats[status] += 1

            # Process aliases for this technology
            if tech_data.alias:
                created, skipped = _process_technology_aliases(
                    service, technology, tech_name, tech_data.alias, logger
                )
                stats["aliases_created"] += created
                stats["aliases_skipped"] += skipped

        # =================================================================
        # SECOND PASS: Establish parent relationships
        # =================================================================
        logger.info("Starting second pass: Establishing parent relationships...")

        for tech_data in new_technologies:
            if not tech_data.parent:
                continue  # Skip technologies without parents

            # Update parent relationship
            if _update_parent_relationship(
                service, tech_data.name, tech_data.parent, technology_map, logger
            ):
                stats["parents_updated"] += 1

        # Completion
        logger.info(
            f"Technology sync completed - "
            f"Created: {stats['created']}, "
            f"Existing: {stats['existing']}, "
            f"Aliases Created: {stats['aliases_created']}, "
            f"Aliases Skipped: {stats['aliases_skipped']}, "
            f"Parents Updated: {stats['parents_updated']}"
        )

    except Exception as e:
        logger.error(f"Error during technology sync: {e}")
        raise
