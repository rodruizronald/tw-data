"""
Service for managing Supabase data operations.

Provides business logic layer for Supabase-backed persistence, handling operations
for companies and other Supabase entities across the application.
"""

import logging
from typing import cast

from core.models.jobs import Job as CoreJob
from data.supebase import supabase_manager
from data.supebase.mappers.job_mapper import JobEnumMapper
from data.supebase.models.company import Company
from data.supebase.models.job import Job as SupabaseJob
from data.supebase.models.job_technology import JobTechnology
from data.supebase.models.technology import Technology
from data.supebase.models.technology_alias import TechnologyAlias
from data.supebase.repositories.companies import CompaniesRepository
from data.supebase.repositories.job_technologies import JobTechnologiesRepository
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
        self.job_technologies = JobTechnologiesRepository(supabase_manager.get_client())
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

    def get_company_by_name(self, name: str) -> Company:
        """
        Get company by name.

        Args:
            name: Company name to search for

        Returns:
            Company instance matching the name

        Raises:
            SupabaseNotFoundError: If company with given name doesn't exist
            SupabaseConnectionError: On connection/network errors
        """
        try:
            logger.info(f"Getting company by name: {name}")
            company = self.companies.get_by_name(name=name)
            logger.info(f"Successfully retrieved company with ID: {company.id}")
            return company
        except Exception as e:
            logger.error(f"Failed to get company '{name}': {e}")
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

            # Map core enums to Supabase enums using JobEnumMapper
            experience_level = JobEnumMapper.map_experience_level(
                job.details.experience_level
            )
            employment_type = JobEnumMapper.map_employment_type(
                job.details.employment_type
            )
            location = JobEnumMapper.map_location(job.details.location)
            province = JobEnumMapper.map_province(job.details.province)
            work_mode = JobEnumMapper.map_work_mode(job.details.work_mode)
            job_function = JobEnumMapper.map_job_function(job.details.job_function)

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

    def job_exists(self, signature: str) -> bool:
        """
        Check if a job with the given signature exists.

        Args:
            signature: Unique job signature to check

        Returns:
            True if job exists, False otherwise

        Raises:
            SupabaseConnectionError: On connection/network errors
        """
        try:
            exists: bool = self.jobs.exists_by_signature(signature=signature)
            return exists
        except Exception as e:
            logger.error(f"Failed to check if job exists: {e}")
            raise

    def update_job(self, job: CoreJob, company_id: int) -> SupabaseJob:
        """
        Update an existing job posting from a core Job model.

        Maps the core Job model fields to the Supabase schema and updates the record.

        Args:
            job: Core Job model containing job details, requirements, and technologies
            company_id: Foreign key reference to companies table

        Returns:
            Updated SupabaseJob instance with all fields populated

        Raises:
            SupabaseNotFoundError: If job with given signature doesn't exist
            SupabaseValidationError: If data violates database constraints
            SupabaseConnectionError: On connection/network errors
            ValueError: If job is missing required details (stage 2 not processed)
        """
        try:
            if not job.is_stage_2_processed or job.details is None:
                raise ValueError("Job must have details (stage 2 processed) to update")

            logger.info(f"Updating job: {job.title} for company_id={company_id}")

            # Map core enums to Supabase enums using JobEnumMapper
            experience_level = JobEnumMapper.map_experience_level(
                job.details.experience_level
            )
            employment_type = JobEnumMapper.map_employment_type(
                job.details.employment_type
            )
            location = JobEnumMapper.map_location(job.details.location)
            province = JobEnumMapper.map_province(job.details.province)
            work_mode = JobEnumMapper.map_work_mode(job.details.work_mode)
            job_function = JobEnumMapper.map_job_function(job.details.job_function)

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

            updated_job = self.jobs.update_by_signature(
                signature=job.signature,
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
            )
            logger.info(f"Successfully updated job with ID: {updated_job.id}")
            return updated_job
        except Exception as e:
            logger.error(f"Failed to update job '{job.title}': {e}")
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

    def deactivate_job(self, signature: str) -> SupabaseJob:
        """
        Deactivate a job posting (soft delete).

        Args:
            signature: Unique job signature to deactivate

        Returns:
            Updated SupabaseJob instance with is_active=False

        Raises:
            SupabaseNotFoundError: If job with given signature doesn't exist
            SupabaseConnectionError: On connection/network errors
        """
        try:
            logger.info(f"Deactivating job with signature: {signature[:20]}...")
            job = self.jobs.deactivate(signature=signature)
            logger.info(f"Successfully deactivated job: {job.title}")
            return job
        except Exception as e:
            logger.error(f"Failed to deactivate job with signature: {e}")
            raise

    def create_job_technology(self, job_id: int, technology_id: int) -> JobTechnology:
        """
        Create a new job-technology association.

        Links a job to a technology in the job_technologies junction table.

        Args:
            job_id: ID of the job to associate
            technology_id: ID of the technology to associate

        Returns:
            Created JobTechnology instance

        Raises:
            SupabaseConflictError: If job-technology association already exists
            SupabaseValidationError: If job_id or technology_id are invalid
            SupabaseConnectionError: On connection/network errors
        """
        try:
            logger.info(
                f"Creating job technology: job_id={job_id}, technology_id={technology_id}"
            )
            job_technology = self.job_technologies.create(
                job_id=job_id, technology_id=technology_id
            )
            logger.info(
                f"Successfully created job technology with ID: {job_technology.id}"
            )
            return job_technology
        except Exception as e:
            logger.error(
                f"Failed to create job technology (job_id={job_id}, technology_id={technology_id}): {e}"
            )
            raise
