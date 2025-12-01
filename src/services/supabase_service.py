"""
Service for managing Supabase data operations.

Provides business logic layer for Supabase-backed persistence, handling operations
for companies and other Supabase entities across the application.
"""

import logging
from typing import cast

from data.supebase import supabase_manager
from data.supebase.models.company import Company
from data.supebase.models.technology import Technology
from data.supebase.models.technology_alias import TechnologyAlias
from data.supebase.repositories.companies import CompaniesRepository
from data.supebase.repositories.technologies import TechnologiesRepository
from data.supebase.repositories.technology_aliases import TechnologyAliasesRepository

logger = logging.getLogger(__name__)


class SupabaseService:
    """Service for handling Supabase database operations."""

    def __init__(self):
        """Initialize Supabase data service."""
        self.companies = CompaniesRepository(supabase_manager.get_client())
        self.technologies = TechnologiesRepository(supabase_manager.get_client())
        self.technology_aliases = TechnologyAliasesRepository(
            supabase_manager.get_client()
        )

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

    def create_technology(self, name: str, parent_id: int | None = None) -> Technology:
        """
        Create a new technology.

        Args:
            name: Technology name (must be unique)
            parent_id: Optional parent technology ID

        Returns:
            Created Technology instance

        Raises:
            SupabaseConflictError: If technology name already exists
            SupabaseValidationError: If name violates database constraints
            SupabaseConnectionError: On connection/network errors
        """
        try:
            logger.info(f"Creating technology: {name} (parent_id={parent_id})")
            technology = self.technologies.create(name=name, parent_id=parent_id)
            logger.info(f"Successfully created technology with ID: {technology.id}")
            return technology
        except Exception as e:
            logger.error(f"Failed to create technology '{name}': {e}")
            raise

    def get_technology_by_name(self, name: str) -> Technology:
        """
        Get technology by name.

        Args:
            name: Technology name to search for

        Returns:
            Technology instance matching the name

        Raises:
            SupabaseNotFoundError: If technology with given name doesn't exist
            SupabaseConnectionError: On connection/network errors
        """
        try:
            logger.info(f"Getting technology by name: {name}")
            technology = self.technologies.get_by_name(name=name)
            logger.info(f"Successfully retrieved technology with ID: {technology.id}")
            return technology
        except Exception as e:
            logger.error(f"Failed to get technology '{name}': {e}")
            raise

    def get_all_technology_names(self) -> list[str]:
        """
        Get all technology names.

        Returns:
            List of all technology names in the database

        Raises:
            SupabaseConnectionError: On connection/network errors
        """
        try:
            names = cast("list[str]", self.technologies.get_all_names())
            logger.info(f"Retrieved {len(names)} technology names")
            return names
        except Exception as e:
            logger.error(f"Failed to get all technology names: {e}")
            raise

    def update_technology(
        self, technology_id: int, name: str | None = None, parent_id: int | None = None
    ) -> Technology:
        """
        Update existing technology.

        Args:
            technology_id: ID of the technology to update
            name: New technology name (optional)
            parent_id: New parent technology ID (optional)

        Returns:
            Updated Technology instance

        Raises:
            SupabaseNotFoundError: If technology with given ID doesn't exist
            SupabaseConflictError: If new name conflicts with existing technology
            SupabaseValidationError: If update violates database constraints
            SupabaseConnectionError: On connection/network errors
        """
        try:
            logger.info(f"Updating technology with ID: {technology_id}")
            technology = self.technologies.update_technology(
                technology_id=technology_id, name=name, parent_id=parent_id
            )
            logger.info(f"Successfully updated technology: {technology.name}")
            return technology
        except Exception as e:
            logger.error(f"Failed to update technology {technology_id}: {e}")
            raise

    def create_technology_alias(
        self, technology_id: int, alias: str
    ) -> TechnologyAlias:
        """
        Create a new technology alias.

        Args:
            technology_id: ID of the technology this alias refers to
            alias: Alias name (must be unique)

        Returns:
            Created TechnologyAlias instance

        Raises:
            SupabaseConflictError: If alias already exists
            SupabaseValidationError: If alias violates database constraints or technology_id is invalid
            SupabaseConnectionError: On connection/network errors
        """
        try:
            logger.info(
                f"Creating technology alias: {alias} for technology_id={technology_id}"
            )
            technology_alias = self.technology_aliases.create(
                technology_id=technology_id, alias=alias
            )
            logger.info(
                f"Successfully created technology alias with ID: {technology_alias.id}"
            )
            return technology_alias
        except Exception as e:
            logger.error(f"Failed to create technology alias '{alias}': {e}")
            raise
