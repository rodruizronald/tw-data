"""
Service for managing Supabase data operations.

Provides business logic layer for Supabase-backed persistence, handling operations
for companies and other Supabase entities across the application.
"""

import logging
from typing import cast

from core.models.jobs import (
    EmploymentType as CoreEmploymentType,
)
from core.models.jobs import (
    ExperienceLevel as CoreExperienceLevel,
)
from core.models.jobs import (
    Job as CoreJob,
)
from core.models.jobs import (
    JobFunction as CoreJobFunction,
)
from core.models.jobs import (
    Location as CoreLocation,
)
from core.models.jobs import (
    WorkMode as CoreWorkMode,
)
from data.supebase import supabase_manager
from data.supebase.models.company import Company
from data.supebase.models.job import (
    EmploymentType,
    ExperienceLevel,
    JobFunction,
    Location,
    Province,
    WorkMode,
)
from data.supebase.models.job import (
    Job as SupabaseJob,
)
from data.supebase.models.technology import Technology
from data.supebase.models.technology_alias import TechnologyAlias
from data.supebase.repositories.companies import CompaniesRepository
from data.supebase.repositories.jobs import JobsRepository
from data.supebase.repositories.technologies import TechnologiesRepository
from data.supebase.repositories.technology_aliases import TechnologyAliasesRepository

logger = logging.getLogger(__name__)


class SupabaseService:
    """Service for handling Supabase database operations."""

    def __init__(self):
        """Initialize Supabase data service."""
        self.companies = CompaniesRepository(supabase_manager.get_client())
        self.jobs = JobsRepository(supabase_manager.get_client())
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

    def create_job(self, job: CoreJob, company_id: int) -> SupabaseJob:
        """
        Create a new job posting from a core Job model.

        Maps the core Job model fields to the Supabase schema and creates the record.

        Args:
            job: Core Job model containing job details, requirements, and technologies
            company_id: Foreign key reference to companies table

        Returns:
            Created SupabaseJob instance with all fields populated

        Raises:
            SupabaseConflictError: If job signature already exists
            SupabaseValidationError: If data violates database constraints
            SupabaseConnectionError: On connection/network errors
            ValueError: If job is missing required details (stage 2 not processed)
        """
        try:
            if not job.is_stage_2_processed or job.details is None:
                raise ValueError("Job must have details (stage 2 processed) to create")

            logger.info(f"Creating job: {job.title} for company_id={company_id}")

            # Map core enums to Supabase enums
            experience_level = self._map_experience_level(job.details.experience_level)
            employment_type = self._map_employment_type(job.details.employment_type)
            location = self._map_location(job.details.location)
            province = self._map_province(job.details.province)
            work_mode = self._map_work_mode(job.details.work_mode)
            job_function = self._map_job_function(job.details.job_function)

            # Extract optional fields from requirements (stage 3)
            responsibilities = None
            skill_must_have = None
            skill_nice_have = None
            benefits = None
            if job.requirements is not None:
                responsibilities = job.requirements.responsibilities or None
                skill_must_have = job.requirements.skill_must_have or None
                skill_nice_have = job.requirements.skill_nice_to_have or None
                benefits = job.requirements.benefits or None

            # Extract main technologies (stage 4)
            main_technologies = None
            if job.technologies is not None:
                main_technologies = job.technologies.main_technologies or None

            created_job = self.jobs.create(
                company_id=company_id,
                title=job.title,
                description=job.details.description,
                experience_level=experience_level,
                employment_type=employment_type,
                location=location,
                city=job.details.city,
                province=province,
                work_mode=work_mode,
                job_function=job_function,
                application_url=job.url,
                responsibilities=responsibilities,
                skill_must_have=skill_must_have,
                skill_nice_have=skill_nice_have,
                main_technologies=main_technologies,
                benefits=benefits,
                signature=job.signature,
            )
            logger.info(f"Successfully created job with ID: {created_job.id}")
            return created_job
        except Exception as e:
            logger.error(f"Failed to create job '{job.title}': {e}")
            raise

    def get_job_by_signature(self, signature: str) -> SupabaseJob:
        """
        Get job by unique signature.

        Args:
            signature: Unique job signature to search for

        Returns:
            SupabaseJob instance matching the signature

        Raises:
            SupabaseNotFoundError: If job with given signature doesn't exist
            SupabaseConnectionError: On connection/network errors
        """
        try:
            logger.info(f"Getting job by signature: {signature[:20]}...")
            job = self.jobs.get_by_signature(signature=signature)
            logger.info(f"Successfully retrieved job with ID: {job.id}")
            return job
        except Exception as e:
            logger.error(f"Failed to get job by signature: {e}")
            raise

    def deactivate_job(self, job_id: int) -> SupabaseJob:
        """
        Deactivate a job posting (soft delete).

        Args:
            job_id: ID of the job to deactivate

        Returns:
            Updated SupabaseJob instance with is_active=False

        Raises:
            SupabaseNotFoundError: If job with given ID doesn't exist
            SupabaseConnectionError: On connection/network errors
        """
        try:
            logger.info(f"Deactivating job with ID: {job_id}")
            job = self.jobs.deactivate(job_id=job_id)
            logger.info(f"Successfully deactivated job: {job.title}")
            return job
        except Exception as e:
            logger.error(f"Failed to deactivate job {job_id}: {e}")
            raise

    def _map_experience_level(self, core_level: CoreExperienceLevel) -> ExperienceLevel:
        """Map core ExperienceLevel enum to Supabase ExperienceLevel enum."""
        mapping = {
            CoreExperienceLevel.ENTRY_LEVEL: ExperienceLevel.ENTRY_LEVEL,
            CoreExperienceLevel.JUNIOR: ExperienceLevel.ENTRY_LEVEL,
            CoreExperienceLevel.MID_LEVEL: ExperienceLevel.MID_LEVEL,
            CoreExperienceLevel.SENIOR: ExperienceLevel.SENIOR,
            CoreExperienceLevel.LEAD: ExperienceLevel.MANAGER,
            CoreExperienceLevel.PRINCIPAL: ExperienceLevel.DIRECTOR,
            CoreExperienceLevel.EXECUTIVE: ExperienceLevel.EXECUTIVE,
        }
        return mapping.get(core_level, ExperienceLevel.MID_LEVEL)

    def _map_employment_type(self, core_type: CoreEmploymentType) -> EmploymentType:
        """Map core EmploymentType enum to Supabase EmploymentType enum."""
        mapping = {
            CoreEmploymentType.FULL_TIME: EmploymentType.FULL_TIME,
            CoreEmploymentType.PART_TIME: EmploymentType.PART_TIME,
            CoreEmploymentType.CONTRACT: EmploymentType.CONTRACTOR,
            CoreEmploymentType.FREELANCE: EmploymentType.CONTRACTOR,
            CoreEmploymentType.TEMPORARY: EmploymentType.TEMPORARY,
            CoreEmploymentType.INTERNSHIP: EmploymentType.INTERNSHIP,
        }
        return mapping.get(core_type, EmploymentType.FULL_TIME)

    def _map_location(self, core_location: CoreLocation) -> Location:
        """Map core Location enum to Supabase Location enum."""
        mapping = {
            CoreLocation.COSTA_RICA: Location.COSTA_RICA,
            CoreLocation.LATAM: Location.LATAM,
        }
        return mapping.get(core_location, Location.LATAM)

    def _map_province(self, province_str: str) -> Province:
        """Map province string to Supabase Province enum."""
        province_mapping = {
            "San Jose": Province.SAN_JOSE,
            "Alajuela": Province.ALAJUELA,
            "Heredia": Province.HEREDIA,
            "Guanacaste": Province.GUANACASTE,
            "Puntarenas": Province.PUNTARENAS,
            "Limon": Province.LIMON,
            "Cartago": Province.CARTAGO,
        }
        return province_mapping.get(province_str, Province.SAN_JOSE)

    def _map_work_mode(self, core_mode: CoreWorkMode) -> WorkMode:
        """Map core WorkMode enum to Supabase WorkMode enum."""
        mapping = {
            CoreWorkMode.REMOTE: WorkMode.REMOTE,
            CoreWorkMode.HYBRID: WorkMode.HYBRID,
            CoreWorkMode.ONSITE: WorkMode.ONSITE,
        }
        return mapping.get(core_mode, WorkMode.REMOTE)

    def _map_job_function(self, core_function: CoreJobFunction) -> JobFunction:
        """Map core JobFunction enum to Supabase JobFunction enum."""
        mapping = {
            CoreJobFunction.TECHNOLOGY_ENGINEERING: JobFunction.TECHNOLOGY_ENGINEERING,
            CoreJobFunction.SALES_BUSINESS_DEVELOPMENT: JobFunction.SALES_BUSINESS_DEVELOPMENT,
            CoreJobFunction.MARKETING_COMMUNICATIONS: JobFunction.MARKETING_COMMUNICATIONS,
            CoreJobFunction.OPERATIONS_LOGISTICS: JobFunction.OPERATIONS_LOGISTICS,
            CoreJobFunction.FINANCE_ACCOUNTING: JobFunction.FINANCE_ACCOUNTING,
            CoreJobFunction.HUMAN_RESOURCES: JobFunction.HUMAN_RESOURCES,
            CoreJobFunction.CUSTOMER_SUCCESS_SUPPORT: JobFunction.CUSTOMER_SUCCESS_SUPPORT,
            CoreJobFunction.PRODUCT_MANAGEMENT: JobFunction.PRODUCT_MANAGEMENT,
            CoreJobFunction.DATA_ANALYTICS: JobFunction.DATA_ANALYTICS,
            CoreJobFunction.HEALTHCARE_MEDICAL: JobFunction.HEALTHCARE_MEDICAL,
            CoreJobFunction.LEGAL_COMPLIANCE: JobFunction.LEGAL_COMPLIANCE,
            CoreJobFunction.DESIGN_CREATIVE: JobFunction.DESIGN_CREATIVE,
            CoreJobFunction.ADMINISTRATIVE_OFFICE: JobFunction.ADMINISTRATIVE_OFFICE,
            CoreJobFunction.CONSULTING_STRATEGY: JobFunction.CONSULTING_STRATEGY,
            CoreJobFunction.GENERAL_MANAGEMENT: JobFunction.GENERAL_MANAGEMENT,
            CoreJobFunction.OTHER: JobFunction.OTHER,
        }
        return mapping.get(core_function, JobFunction.OTHER)
