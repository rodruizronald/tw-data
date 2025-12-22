"""
Job domain model.

Represents the jobs table schema with type safety and validation.
Includes enum types that match the PostgreSQL enum types in the database.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class JobFunction(StrEnum):
    """
    Job function enumeration for job postings.

    Represents the functional area or department of the job.
    Values match the job_function_enum PostgreSQL type.
    """

    TECHNOLOGY_ENGINEERING = "technology-engineering"
    SALES_BUSINESS_DEVELOPMENT = "sales-business-development"
    MARKETING_COMMUNICATIONS = "marketing-communications"
    OPERATIONS_LOGISTICS = "operations-logistics"
    FINANCE_ACCOUNTING = "finance-accounting"
    HUMAN_RESOURCES = "human-resources"
    CUSTOMER_SUCCESS_SUPPORT = "customer-success-support"
    PRODUCT_MANAGEMENT = "product-management"
    DATA_ANALYTICS = "data-analytics"
    HEALTHCARE_MEDICAL = "healthcare-medical"
    LEGAL_COMPLIANCE = "legal-compliance"
    DESIGN_CREATIVE = "design-creative"
    ADMINISTRATIVE_OFFICE = "administrative-office"
    CONSULTING_STRATEGY = "consulting-strategy"
    GENERAL_MANAGEMENT = "general-management"
    OTHER = "other"


class Province(StrEnum):
    """
    Province enumeration for Costa Rican locations.

    Represents the provinces (administrative divisions) of Costa Rica.
    Values match the province_enum PostgreSQL type.
    """

    SAN_JOSE = "san-jose"
    ALAJUELA = "alajuela"
    HEREDIA = "heredia"
    GUANACASTE = "guanacaste"
    PUNTARENAS = "puntarenas"
    LIMON = "limon"
    CARTAGO = "cartago"


class ExperienceLevel(StrEnum):
    """
    Experience level enumeration for job postings.

    Represents the seniority level required for a position.
    Values match the experience_level_enum PostgreSQL type.
    """

    ENTRY_LEVEL = "entry-level"
    MID_LEVEL = "mid-level"
    SENIOR = "senior"
    MANAGER = "manager"
    DIRECTOR = "director"
    EXECUTIVE = "executive"


class EmploymentType(StrEnum):
    """
    Employment type enumeration for job postings.

    Represents the type of employment relationship offered.
    Values match the employment_type_enum PostgreSQL type.
    """

    FULL_TIME = "full-time"
    PART_TIME = "part-time"
    CONTRACTOR = "contractor"
    TEMPORARY = "temporary"
    INTERNSHIP = "internship"


class WorkMode(StrEnum):
    """
    Work mode enumeration for job postings.

    Represents the work arrangement (location-based).
    Values match the work_mode_enum PostgreSQL type.
    """

    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class Location(StrEnum):
    """
    Location enumeration for job postings.

    Represents the geographic region where the job is available.
    Values match the location_enum PostgreSQL type.
    """

    COSTA_RICA = "costa-rica"
    LATAM = "latam"


class Job(BaseModel):
    """
    Domain model for jobs table.

    Schema:
        id: Unique identifier (auto-generated)
        company_id: Foreign key reference to companies table
        title: Job title (max 255 chars)
        description: Full job description
        responsibilities: List of job responsibilities
        skill_must_have: Required skills for the position
        skill_nice_have: Nice-to-have skills for the position
        main_technologies: Main technologies used in the role
        benefits: Job benefits offered
        experience_level: Required seniority level
        employment_type: Type of employment
        location: Geographic region (costa-rica or latam)
        city: City where the job is located
        province: Province in Costa Rica
        work_mode: Work arrangement (remote/hybrid/onsite)
        job_function: Functional area or department
        application_url: URL to apply for the job
        is_active: Whether the job posting is active (soft delete flag)
        signature: Unique hash signature for deduplication
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated

    Example:
        ```python
        job = Job(
            id=1,
            company_id=5,
            title="Senior Python Developer",
            description="We are looking for...",
            responsibilities=["Design APIs", "Write tests"],
            skill_must_have=["Python", "FastAPI"],
            skill_nice_have=["Docker", "AWS"],
            main_technologies=["Python", "PostgreSQL"],
            benefits=["Health insurance", "Remote work"],
            experience_level=ExperienceLevel.SENIOR,
            employment_type=EmploymentType.FULL_TIME,
            location=Location.COSTA_RICA,
            city="San José",
            province=Province.SAN_JOSE,
            work_mode=WorkMode.REMOTE,
            job_function=JobFunction.TECHNOLOGY_ENGINEERING,
            application_url="https://example.com/apply",
            is_active=True,
            signature="abc123def456...",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        print(job.title)  # "Senior Python Developer"
        ```
    """

    id: int = Field(..., description="Unique job identifier")
    company_id: int = Field(..., description="Foreign key to companies table")
    title: str = Field(..., max_length=255, description="Job title")
    description: str = Field(..., description="Full job description")
    responsibilities: list[str] | None = Field(
        default=None, description="List of job responsibilities"
    )
    skill_must_have: list[str] | None = Field(
        default=None, description="Required skills for the position"
    )
    skill_nice_have: list[str] | None = Field(
        default=None, description="Nice-to-have skills for the position"
    )
    main_technologies: list[str] | None = Field(
        default=None, description="Main technologies used in the role"
    )
    benefits: list[str] | None = Field(default=None, description="Job benefits offered")
    experience_level: ExperienceLevel = Field(
        ..., description="Required seniority level"
    )
    employment_type: EmploymentType = Field(..., description="Type of employment")
    location: Location = Field(..., description="Geographic region")
    city: str = Field(..., max_length=50, description="City where the job is located")
    province: Province = Field(..., description="Province in Costa Rica")
    work_mode: WorkMode = Field(..., description="Work arrangement")
    job_function: JobFunction = Field(..., description="Functional area or department")
    application_url: str = Field(
        ..., max_length=255, description="URL to apply for the job"
    )
    is_active: bool = Field(default=True, description="Active status (soft delete)")
    signature: str | None = Field(
        default=None,
        max_length=64,
        description="Unique hash signature for deduplication",
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        """Pydantic model configuration."""

        # Allow creating model from ORM objects or dicts
        from_attributes = True

    def __repr__(self) -> str:
        """String representation for debugging."""
        status = "active" if self.is_active else "inactive"
        return f"Job(id={self.id}, title='{self.title}', status={status})"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.title} (ID: {self.id})"
