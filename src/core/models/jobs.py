from dataclasses import dataclass
from enum import Enum
from typing import Any

from core.config.services import WebParserConfig
from core.models.parsers import ParserType


class Location(str, Enum):
    COSTA_RICA = "Costa Rica"
    LATAM = "LATAM"


class WorkMode(str, Enum):
    REMOTE = "Remote"
    HYBRID = "Hybrid"
    ONSITE = "Onsite"


class EmploymentType(str, Enum):
    FULL_TIME = "Full-time"
    PART_TIME = "Part-time"
    CONTRACT = "Contract"
    FREELANCE = "Freelance"
    TEMPORARY = "Temporary"
    INTERNSHIP = "Internship"


class ExperienceLevel(str, Enum):
    ENTRY_LEVEL = "Entry-level"
    JUNIOR = "Junior"
    MID_LEVEL = "Mid-level"
    SENIOR = "Senior"
    LEAD = "Lead"
    PRINCIPAL = "Principal"
    EXECUTIVE = "Executive"


class JobFunction(str, Enum):
    TECHNOLOGY_ENGINEERING = "Technology & Engineering"
    SALES_BUSINESS_DEVELOPMENT = "Sales & Business Development"
    MARKETING_COMMUNICATIONS = "Marketing & Communications"
    OPERATIONS_LOGISTICS = "Operations & Logistics"
    FINANCE_ACCOUNTING = "Finance & Accounting"
    HUMAN_RESOURCES = "Human Resources"
    CUSTOMER_SUCCESS_SUPPORT = "Customer Success & Support"
    PRODUCT_MANAGEMENT = "Product Management"
    DATA_ANALYTICS = "Data & Analytics"
    HEALTHCARE_MEDICAL = "Healthcare & Medical"
    LEGAL_COMPLIANCE = "Legal & Compliance"
    DESIGN_CREATIVE = "Design & Creative"
    ADMINISTRATIVE_OFFICE = "Administrative & Office"
    CONSULTING_STRATEGY = "Consulting & Strategy"
    GENERAL_MANAGEMENT = "General Management"
    OTHER = "Other"


class Province(str, Enum):
    SAN_JOSE = "San Jose"
    ALAJUELA = "Alajuela"
    HEREDIA = "Heredia"
    GUANACASTE = "Guanacaste"
    PUNTARENAS = "Puntarenas"
    LIMON = "Limon"
    CARTAGO = "Cartago"


@dataclass
class CompanyData:
    """Data structure for company information."""

    name: str
    career_url: str
    web_parser: dict[str, Any] | WebParserConfig
    enabled: bool = True

    # After __post_init__, web_parser is always WebParserConfig
    def __post_init__(self):
        """Validate and normalize data after initialization."""
        if not self.name or not self.career_url:
            raise ValueError("Company name and career_url are required")

        # Convert web_parser dict to WebParserConfig object
        if isinstance(self.web_parser, dict):
            self.web_parser = WebParserConfig(
                type=self.web_parser.get("type", "default"),
                selectors=self.web_parser.get("selectors", {}),
            )

    @property
    def web_parser_config(self) -> WebParserConfig:
        """Get parser type."""
        assert isinstance(self.web_parser, WebParserConfig)
        return self.web_parser

    @property
    def parser_type(self) -> ParserType:
        """Get parser type."""
        assert isinstance(self.web_parser, WebParserConfig)
        parser_type: ParserType = self.web_parser.parser_type
        return parser_type

    @property
    def job_board_selectors(self) -> list[str]:
        """Get job board selectors."""
        assert isinstance(self.web_parser, WebParserConfig)
        selectors: list[str] = self.web_parser.job_board_selectors
        return selectors

    @property
    def job_card_selectors(self) -> list[str]:
        """Get job card selectors."""
        assert isinstance(self.web_parser, WebParserConfig)
        selectors: list[str] = self.web_parser.job_card_selectors
        return selectors

    def to_dict(self) -> dict[str, Any]:
        """Convert CompanyData to dictionary for JSON serialization."""
        assert isinstance(self.web_parser, WebParserConfig)
        return {
            "name": self.name,
            "career_url": self.career_url,
            "web_parser": {
                "type": self.web_parser.type,
                "selectors": self.web_parser.selectors,
            },
            "enabled": self.enabled,
        }


@dataclass
class JobDetails:
    """Job details extracted from Stage 2 analysis."""

    location: Location
    work_mode: WorkMode
    employment_type: EmploymentType
    experience_level: ExperienceLevel
    job_function: JobFunction
    province: str  # Province name or empty string for LATAM
    city: str  # City name or empty string
    description: str

    def to_dict(self) -> dict[str, Any]:
        """Convert JobDetails to dictionary for JSON serialization."""
        return {
            "location": self.location.value,
            "work_mode": self.work_mode.value,
            "employment_type": self.employment_type.value,
            "experience_level": self.experience_level.value,
            "job_function": self.job_function.value,
            "province": self.province,
            "city": self.city,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JobDetails":
        """Create JobDetails from dictionary."""
        return cls(
            location=Location(data.get("location", Location.LATAM.value)),
            work_mode=WorkMode(data.get("work_mode", WorkMode.REMOTE.value)),
            employment_type=EmploymentType(
                data.get("employment_type", EmploymentType.FULL_TIME.value)
            ),
            experience_level=ExperienceLevel(
                data.get("experience_level", ExperienceLevel.MID_LEVEL.value)
            ),
            job_function=JobFunction(data.get("job_function", JobFunction.OTHER.value)),
            province=data.get("province", ""),
            city=data.get("city", ""),
            description=data.get("description", ""),
        )


@dataclass
class JobRequirements:
    """Job skills and responsibilities extracted from Stage 3 analysis."""

    responsibilities: list[str]
    skill_must_have: list[str]
    skill_nice_to_have: list[str]
    benefits: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert JobRequirements to dictionary for JSON serialization."""
        return {
            "responsibilities": self.responsibilities,
            "skill_must_have": self.skill_must_have,
            "skill_nice_to_have": self.skill_nice_to_have,
            "benefits": self.benefits,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JobRequirements":
        """Create JobRequirements from dictionary."""
        return cls(
            responsibilities=data.get("responsibilities", []),
            skill_must_have=data.get("skill_must_have", []),
            skill_nice_to_have=data.get("skill_nice_to_have", []),
            benefits=data.get("benefits", []),
        )


@dataclass
class Technology:
    """Individual technology with categorization and requirement status."""

    name: str
    category: str
    required: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert Technology to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "category": self.category,
            "required": self.required,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Technology":
        """Create Technology from dictionary."""
        return cls(
            name=data.get("name", ""),
            category=data.get("category", ""),
            required=data.get("required", False),
        )


@dataclass
class JobTechnologies:
    """Job technologies extracted from Stage 4 analysis."""

    technologies: list[Technology]
    main_technologies: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert JobTechnologies to dictionary for JSON serialization."""
        return {
            "technologies": [tech.to_dict() for tech in self.technologies],
            "main_technologies": self.main_technologies,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JobTechnologies":
        """Create JobTechnologies from dictionary."""
        return cls(
            technologies=[
                Technology.from_dict(tech_data)
                for tech_data in data.get("technologies", [])
            ],
            main_technologies=data.get("main_technologies", []),
        )


@dataclass
class TechData:
    """Technology data model."""

    name: str
    alias: list[str]
    parent: str
    is_parent: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TechData":
        """Create TechData from dictionary."""
        return cls(
            name=data.get("name", ""),
            alias=data.get("alias", []),
            parent=data.get("parent", ""),
            is_parent=data.get("is_parent", False),
        )


@dataclass
class Job:
    """Evolving job model that grows through pipeline stages."""

    # Stage 1 data (always present)
    title: str
    url: str
    signature: str
    company: str

    # Stage 2 data (optional, populated after stage 2)
    details: JobDetails | None = None

    # Stage 3 data (optional, populated after stage 3)
    requirements: JobRequirements | None = None

    # Stage 4 data (optional, populated after stage 4)
    technologies: JobTechnologies | None = None

    @property
    def is_stage_2_processed(self) -> bool:
        """Check if job has been processed through Stage 2."""
        return self.details is not None

    @property
    def is_stage_3_processed(self) -> bool:
        """Check if job has been processed through Stage 3."""
        return self.requirements is not None

    @property
    def is_stage_4_processed(self) -> bool:
        """Check if job has been processed through Stage 4."""
        return self.technologies is not None

    @property
    def is_eligible(self) -> bool:
        """Check if job has been processed and has details (Stage 2 processing complete)."""
        return self.details is not None

    def to_dict(self) -> dict[str, Any]:
        """Convert Job to dictionary for JSON serialization."""
        result: dict[str, Any] = {
            "title": self.title,
            "url": self.url,
            "signature": self.signature,
            "company": self.company,
        }

        # Add optional stage data if present
        if self.details is not None:
            result["details"] = self.details.to_dict()

        if self.requirements is not None:
            result["requirements"] = self.requirements.to_dict()

        if self.technologies is not None:
            result["technologies"] = self.technologies.to_dict()

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Job":
        """Create Job from dictionary."""
        # Extract required Stage 1 fields
        job = cls(
            title=data.get("title", ""),
            url=data.get("url", ""),
            signature=data.get("signature", ""),
            company=data.get("company", ""),
        )

        # Add optional stage data if present
        if "details" in data and data["details"] is not None:
            job.details = JobDetails.from_dict(data["details"])

        if "requirements" in data and data["requirements"] is not None:
            job.requirements = JobRequirements.from_dict(data["requirements"])

        if "technologies" in data and data["technologies"] is not None:
            job.technologies = JobTechnologies.from_dict(data["technologies"])

        return job

    def __post_init__(self):
        """Validate required fields."""
        if not self.title:
            raise ValueError("Job title is required")
        if not self.url:
            raise ValueError("Job URL is required")
