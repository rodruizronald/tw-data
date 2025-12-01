"""
Service for managing Supabase data operations.

Provides business logic layer for Supabase-backed persistence, handling operations
for companies and other Supabase entities across the application.
"""

import logging
from typing import cast

from data.supebase import supabase_manager
from data.supebase.models.company import Company
from data.supebase.repositories.companies import CompaniesRepository

logger = logging.getLogger(__name__)


class SupabaseService:
    """Service for handling Supabase database operations."""

    def __init__(self):
        """Initialize Supabase data service."""
        self.companies = CompaniesRepository(supabase_manager.get_client())

    def create_company(self, name: str, is_active: bool = True) -> Company:
        """
        Create a new company.

        Args:
            name: Company name (must be unique)
            is_active: Whether the company should be active (default: True)

        Returns:
            Created Company instance

        Raises:
            SupabaseConflictError: If company name already exists
            SupabaseValidationError: If name violates database constraints
            SupabaseConnectionError: On connection/network errors
        """
        try:
            logger.info(f"Creating company: {name} (is_active={is_active})")
            company = self.companies.create(name=name, is_active=is_active)
            logger.info(f"Successfully created company with ID: {company.id}")
            return company
        except Exception as e:
            logger.error(f"Failed to create company '{name}': {e}")
            raise

    def get_active_companies(self) -> list[Company]:
        """
        Get all active companies.

        Returns:
            List of active Company instances (empty list if none exist)

        Raises:
            SupabaseConnectionError: On connection/network errors
        """
        try:
            companies = cast("list[Company]", self.companies.get_active())
            logger.info(f"Retrieved {len(companies)} active companies")
            return companies
        except Exception as e:
            logger.error(f"Failed to get active companies: {e}")
            raise

    def get_all_companies(self) -> list[Company]:
        """
        Get all companies (active and inactive).

        Returns:
            List of all Company instances (empty list if none exist)

        Raises:
            SupabaseConnectionError: On connection/network errors
        """
        try:
            companies = cast("list[Company]", self.companies.get_all())
            logger.info(f"Retrieved {len(companies)} companies")
            return companies
        except Exception as e:
            logger.error(f"Failed to get all companies: {e}")
            raise

    def deactivate_company(self, company_id: int) -> Company:
        """
        Deactivate a company (soft delete).

        Args:
            company_id: ID of the company to deactivate

        Returns:
            Updated Company instance with is_active=False

        Raises:
            SupabaseNotFoundError: If company with given ID doesn't exist
            SupabaseConnectionError: On connection/network errors
        """
        try:
            logger.info(f"Deactivating company with ID: {company_id}")
            company = self.companies.deactivate(company_id=company_id)
            logger.info(f"Successfully deactivated company: {company.name}")
            return company
        except Exception as e:
            logger.error(f"Failed to deactivate company {company_id}: {e}")
            raise

    def activate_company(self, company_id: int) -> Company:
        """
        Activate a company (or reactivate an inactive one).

        Args:
            company_id: ID of the company to activate

        Returns:
            Updated Company instance with is_active=True

        Raises:
            SupabaseNotFoundError: If company with given ID doesn't exist
            SupabaseConnectionError: On connection/network errors
        """
        try:
            logger.info(f"Activating company with ID: {company_id}")
            company = self.companies.activate(company_id=company_id)
            logger.info(f"Successfully activated company: {company.name}")
            return company
        except Exception as e:
            logger.error(f"Failed to activate company {company_id}: {e}")
            raise
