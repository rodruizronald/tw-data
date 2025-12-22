"""
Mappers for converting between core job enums and Supabase job enums.

This module provides mapping utilities for converting between the core domain model
enums and Supabase-specific enum types used in the jobs table.
"""

from core.models.jobs import (
    EmploymentType as CoreEmploymentType,
)
from core.models.jobs import (
    ExperienceLevel as CoreExperienceLevel,
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
from data.supebase.models.job import (
    EmploymentType,
    ExperienceLevel,
    JobFunction,
    Location,
    Province,
    WorkMode,
)


class JobEnumMapper:
    """
    Mapper for converting between core job enums and Supabase job enums.

    Provides static methods for mapping enum values from the core domain layer
    to the Supabase database layer.
    """

    @staticmethod
    def map_experience_level(core_level: CoreExperienceLevel) -> ExperienceLevel:
        """
        Map core ExperienceLevel enum to Supabase ExperienceLevel enum.

        Args:
            core_level: Experience level from core domain model

        Returns:
            Corresponding Supabase ExperienceLevel enum value
        """
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

    @staticmethod
    def map_employment_type(core_type: CoreEmploymentType) -> EmploymentType:
        """
        Map core EmploymentType enum to Supabase EmploymentType enum.

        Args:
            core_type: Employment type from core domain model

        Returns:
            Corresponding Supabase EmploymentType enum value
        """
        mapping = {
            CoreEmploymentType.FULL_TIME: EmploymentType.FULL_TIME,
            CoreEmploymentType.PART_TIME: EmploymentType.PART_TIME,
            CoreEmploymentType.CONTRACT: EmploymentType.CONTRACTOR,
            CoreEmploymentType.FREELANCE: EmploymentType.CONTRACTOR,
            CoreEmploymentType.TEMPORARY: EmploymentType.TEMPORARY,
            CoreEmploymentType.INTERNSHIP: EmploymentType.INTERNSHIP,
        }
        return mapping.get(core_type, EmploymentType.FULL_TIME)

    @staticmethod
    def map_location(core_location: CoreLocation) -> Location:
        """
        Map core Location enum to Supabase Location enum.

        Args:
            core_location: Location from core domain model

        Returns:
            Corresponding Supabase Location enum value
        """
        mapping = {
            CoreLocation.COSTA_RICA: Location.COSTA_RICA,
            CoreLocation.LATAM: Location.LATAM,
        }
        return mapping.get(core_location, Location.LATAM)

    @staticmethod
    def map_province(province_str: str) -> Province:
        """
        Map province string to Supabase Province enum.

        Args:
            province_str: Province name string from core domain model

        Returns:
            Corresponding Supabase Province enum value
        """
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

    @staticmethod
    def map_work_mode(core_mode: CoreWorkMode) -> WorkMode:
        """
        Map core WorkMode enum to Supabase WorkMode enum.

        Args:
            core_mode: Work mode from core domain model

        Returns:
            Corresponding Supabase WorkMode enum value
        """
        mapping = {
            CoreWorkMode.REMOTE: WorkMode.REMOTE,
            CoreWorkMode.HYBRID: WorkMode.HYBRID,
            CoreWorkMode.ONSITE: WorkMode.ONSITE,
        }
        return mapping.get(core_mode, WorkMode.REMOTE)

    @staticmethod
    def map_job_function(core_function: CoreJobFunction) -> JobFunction:
        """
        Map core JobFunction enum to Supabase JobFunction enum.

        Args:
            core_function: Job function from core domain model

        Returns:
            Corresponding Supabase JobFunction enum value
        """
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
