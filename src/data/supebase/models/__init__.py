"""
Domain models for Supabase tables.

This package contains Pydantic models representing database entities.
These models provide type safety, validation, and clear contracts for data structures.
"""

from data.supebase.models.company import Company
from data.supebase.models.technology import Technology
from data.supebase.models.technology_alias import TechnologyAlias

__all__ = [
    "Company",
    "Technology",
    "TechnologyAlias",
]
