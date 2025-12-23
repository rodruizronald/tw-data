"""
Database model for unmatched technology storage.

This module contains the UnmatchedTechnology model for storing technologies
found in job postings that don't exist in the Supabase technology database.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from bson import ObjectId

from utils.timezone import now_utc, utc_to_local


@dataclass
class UnmatchedTechnology:
    """
    Database model for unmatched technologies.

    This model represents technologies found in job postings that couldn't
    be matched to any existing technology or alias in the Supabase database.
    """

    # Core fields
    name: str  # Technology name (unique)

    # Database metadata
    _id: ObjectId | None = None
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)

    def __post_init__(self) -> None:
        """Validate required fields after initialization."""
        if not self.name:
            raise ValueError("Technology name is required")

    @property
    def created_at_local(self) -> datetime:
        """Get created_at in local timezone."""
        local_time: datetime = utc_to_local(self.created_at)
        return local_time

    @property
    def updated_at_local(self) -> datetime:
        """Get updated_at in local timezone."""
        local_time: datetime = utc_to_local(self.updated_at)
        return local_time

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = now_utc()

    def to_dict(self) -> dict[str, Any]:
        """
        Convert UnmatchedTechnology to dictionary for MongoDB storage.

        Returns:
            dict: Dictionary representation suitable for MongoDB
        """
        result: dict[str, Any] = {
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

        # Add MongoDB ObjectId if present
        if self._id is not None:
            result["_id"] = self._id

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UnmatchedTechnology":
        """
        Create UnmatchedTechnology from dictionary (e.g., from MongoDB).

        Args:
            data: Dictionary containing unmatched technology data

        Returns:
            UnmatchedTechnology: Created instance
        """
        unmatched_tech = cls(
            name=data.get("name", ""),
        )

        # Set MongoDB metadata
        unmatched_tech._id = data.get("_id")

        # Set timestamps
        if "created_at" in data:
            unmatched_tech.created_at = data["created_at"]
        if "updated_at" in data:
            unmatched_tech.updated_at = data["updated_at"]

        return unmatched_tech

    def __str__(self) -> str:
        """String representation of UnmatchedTechnology."""
        return f"UnmatchedTechnology(name='{self.name}')"

    def __repr__(self) -> str:
        """Detailed string representation of UnmatchedTechnology."""
        return f"UnmatchedTechnology(name='{self.name}', created_at={self.created_at})"
