"""
Domain models for Supabase tables.

This package contains Pydantic models representing database entities.
These models provide type safety, validation, and clear contracts for data structures.
"""

from data.supebase.models.company import Company

__all__ = [
    "Company",
]
