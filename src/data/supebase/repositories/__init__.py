"""
Table-specific repositories for Supabase data access.

This package contains repository implementations that extend BaseRepository
with table-specific operations and business logic.
"""

from data.supebase.repositories.companies import CompaniesRepository
from data.supebase.repositories.job_technologies import JobTechnologiesRepository
from data.supebase.repositories.jobs import JobsRepository
from data.supebase.repositories.technologies import TechnologiesRepository
from data.supebase.repositories.technology_aliases import TechnologyAliasesRepository

__all__ = [
    "CompaniesRepository",
    "JobTechnologiesRepository",
    "JobsRepository",
    "TechnologiesRepository",
    "TechnologyAliasesRepository",
]
