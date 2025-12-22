"""
Jobs repository for managing job posting records.

Provides type-safe CRUD operations for the jobs table with domain model integration.
"""

from datetime import UTC, datetime

from supabase import Client

from data.supebase.base_repository import BaseRepository
from data.supebase.exceptions import SupabaseNotFoundError
from data.supebase.models.job import (
    EmploymentType,
    ExperienceLevel,
    Job,
    JobFunction,
    Location,
    Province,
    WorkMode,
)


class JobsRepository(BaseRepository):
    """
    Repository for jobs table operations.

    Provides methods to:
    - Create new job postings
    - Retrieve jobs by unique signature
    - Deactivate job postings (soft delete)

    All methods return type-safe Job domain models.
    """

    def __init__(self, client: Client) -> None:
        """
        Initialize jobs repository.

        Args:
            client: Supabase client instance
        """
        super().__init__(client, "jobs")

    def create(
        self,
        company_id: int,
        title: str,
        description: str,
        experience_level: ExperienceLevel,
        employment_type: EmploymentType,
        location: Location,
        city: str,
        province: Province,
        work_mode: WorkMode,
        job_function: JobFunction,
        application_url: str,
        responsibilities: list[str] | None = None,
        skill_must_have: list[str] | None = None,
        skill_nice_have: list[str] | None = None,
        main_technologies: list[str] | None = None,
        benefits: list[str] | None = None,
        signature: str | None = None,
        is_active: bool = True,
    ) -> Job:
        """
        Create a new job posting.

        Args:
            company_id: Foreign key reference to companies table
            title: Job title
            description: Full job description
            experience_level: Required seniority level
            employment_type: Type of employment
            location: Geographic region (costa-rica or latam)
            city: City where the job is located
            province: Province in Costa Rica
            work_mode: Work arrangement (remote/hybrid/onsite)
            job_function: Functional area or department
            application_url: URL to apply for the job
            responsibilities: List of job responsibilities (optional)
            skill_must_have: Required skills for the position (optional)
            skill_nice_have: Nice-to-have skills for the position (optional)
            main_technologies: Main technologies used in the role (optional)
            benefits: Job benefits offered (optional)
            signature: Unique hash signature for deduplication (optional)
            is_active: Whether the job should be active (default: True)

        Returns:
            Created Job instance with all fields populated

        Raises:
            SupabaseConflictError: If job signature already exists
            SupabaseValidationError: If data violates database constraints
            SupabaseConnectionError: On connection/network errors

        Example:
            ```python
            repo = JobsRepository(client)
            job = repo.create(
                company_id=1,
                title="Senior Python Developer",
                description="We are looking for...",
                experience_level=ExperienceLevel.SENIOR,
                employment_type=EmploymentType.FULL_TIME,
                location=Location.COSTA_RICA,
                city="San José",
                province=Province.SAN_JOSE,
                work_mode=WorkMode.REMOTE,
                job_function=JobFunction.TECHNOLOGY_ENGINEERING,
                application_url="https://example.com/apply",
                signature="abc123..."
            )
            print(job.id)  # Auto-generated ID
            ```
        """
        # Build insert data with required fields
        data: dict = {
            "company_id": company_id,
            "title": title,
            "description": description,
            "experience_level": experience_level.value,
            "employment_type": employment_type.value,
            "location": location.value,
            "city": city,
            "province": province.value,
            "work_mode": work_mode.value,
            "job_function": job_function.value,
            "application_url": application_url,
            "is_active": is_active,
        }

        # Add optional fields if provided
        if responsibilities is not None:
            data["responsibilities"] = responsibilities
        if skill_must_have is not None:
            data["skill_must_have"] = skill_must_have
        if skill_nice_have is not None:
            data["skill_nice_have"] = skill_nice_have
        if main_technologies is not None:
            data["main_technologies"] = main_technologies
        if benefits is not None:
            data["benefits"] = benefits
        if signature is not None:
            data["signature"] = signature

        # Insert record (timestamps auto-generated by DB)
        result = self.insert(data)

        # Handle response - insert returns list or single dict
        data_result = result[0] if isinstance(result, list) else result

        # Convert to domain model
        job = Job(**data_result)

        return job

    def get_by_signature(self, signature: str) -> Job:
        """
        Get job by unique signature.

        The signature is a unique hash used for deduplication of job postings.

        Args:
            signature: Unique job signature to search for

        Returns:
            Job instance matching the signature

        Raises:
            SupabaseNotFoundError: If job with given signature doesn't exist
            SupabaseConnectionError: On connection/network errors

        Example:
            ```python
            repo = JobsRepository(client)
            job = repo.get_by_signature(signature="abc123def456...")
            print(job.title)  # "Senior Python Developer"
            ```
        """
        # Query by signature
        records = self.select(filters={"signature": signature}, limit=1)

        # Check if job was found
        if not records or len(records) == 0:
            raise SupabaseNotFoundError(f"Job with signature '{signature}' not found")

        # Convert to domain model
        job = Job(**records[0])

        return job

    def deactivate(self, job_id: int) -> Job:
        """
        Deactivate a job posting (soft delete).

        Sets is_active=False and updates the updated_at timestamp.

        Args:
            job_id: ID of the job to deactivate

        Returns:
            Updated Job instance with is_active=False

        Raises:
            SupabaseNotFoundError: If job with given ID doesn't exist
            SupabaseConnectionError: On connection/network errors

        Example:
            ```python
            repo = JobsRepository(client)
            deactivated = repo.deactivate(job_id=5)
            assert deactivated.is_active is False
            ```
        """
        # Update is_active and updated_at
        result = self.update(
            data={
                "is_active": False,
                "updated_at": datetime.now(UTC).isoformat(),
            },
            filters={"id": job_id},
        )

        # Handle response - check if job was found
        if not result or (isinstance(result, list) and len(result) == 0):
            raise SupabaseNotFoundError(
                f"Job with ID {job_id} not found or already deactivated"
            )

        data = result[0] if isinstance(result, list) else result
        job = Job(**data)

        return job
