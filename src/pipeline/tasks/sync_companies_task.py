"""Task for synchronizing companies with the backend."""

from prefect import get_run_logger, task

from core.models.jobs import CompanyData
from services.supabase_data_service import SupabaseDataService


@task(
    name="sync_companies",
    description="Synchronize companies from YAML with backend",
    retries=2,
    retry_delay_seconds=10,
)
def sync_companies_task(companies_from_yaml: list[CompanyData]) -> dict[str, int]:
    """
    Synchronize companies with the backend.

    Compares companies from YAML file with existing companies in the backend
    and performs the following operations:
    - Creates companies that don't exist in the backend
    - Activates companies that are enabled in YAML but inactive in backend
    - Deactivates companies that are disabled in YAML but active in backend

    Args:
        companies_from_yaml: List of companies loaded from companies.yaml

    Returns:
        Dictionary with sync statistics:
        - total_yaml: Total companies in YAML
        - total_backend: Total companies in backend after sync
        - created: Number of companies created
        - activated: Number of companies activated
        - deactivated: Number of companies deactivated
        - already_synced: Number of companies already in correct state
    """
    logger = get_run_logger()

    logger.info(
        f"Starting company sync with {len(companies_from_yaml)} companies from YAML"
    )

    stats = {
        "total_yaml": len(companies_from_yaml),
        "total_backend": 0,
        "created": 0,
        "activated": 0,
        "deactivated": 0,
        "already_synced": 0,
    }

    try:
        service = SupabaseDataService()

        # Fetch all existing companies from backend (active and inactive)
        logger.info("Fetching existing companies from backend...")
        existing_companies = service.get_all_companies()

        # Create a mapping of company name (lowercase) to Company object
        existing_companies_map = {
            company.name.lower(): company for company in existing_companies
        }

        logger.info(f"Found {len(existing_companies)} existing companies in backend")

        # Compare and sync companies
        for company_data in companies_from_yaml:
            company_name_lower = company_data.name.lower()
            desired_active_state = company_data.enabled

            if company_name_lower not in existing_companies_map:
                # Company doesn't exist - create it
                created_company = service.create_company(
                    name=company_data.name,
                    is_active=desired_active_state,
                )

                if created_company:
                    stats["created"] += 1
                    # Add to map for future reference
                    existing_companies_map[company_name_lower] = created_company

            else:
                # Company exists - check if activation status needs to be updated
                existing_company = existing_companies_map[company_name_lower]
                current_active_state = existing_company.is_active

                if current_active_state == desired_active_state:
                    # Already in correct state
                    stats["already_synced"] += 1

                elif desired_active_state and not current_active_state:
                    # Should be active but is inactive - activate it
                    activated_company = service.activate_company(existing_company.id)
                    stats["activated"] += 1
                    # Update map
                    existing_companies_map[company_name_lower] = activated_company

                elif not desired_active_state and current_active_state:
                    # Should be inactive but is active - deactivate it
                    deactivated_company = service.deactivate_company(
                        existing_company.id
                    )
                    stats["deactivated"] += 1
                    # Update map
                    existing_companies_map[company_name_lower] = deactivated_company

        # Get final count of companies in backend
        final_companies = service.get_all_companies()
        stats["total_backend"] = len(final_companies)

        logger.info(
            f"Company sync completed - "
            f"Created: {stats['created']}, "
            f"Activated: {stats['activated']}, "
            f"Deactivated: {stats['deactivated']}, "
            f"Already synced: {stats['already_synced']}, "
            f"Total in backend: {stats['total_backend']}"
        )

        return stats

    except Exception as e:
        logger.error(f"Error during company sync: {e}")
        raise
