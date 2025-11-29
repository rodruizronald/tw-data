"""
Table-specific repositories for Supabase data access.

This package contains repository implementations that extend BaseRepository
with table-specific operations and business logic.
"""

from data.supebase.repositories.companies import CompaniesRepository

__all__ = [
    "CompaniesRepository",
]
