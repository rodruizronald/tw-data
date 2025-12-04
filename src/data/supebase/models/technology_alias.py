"""
Technology Alias domain model.

Represents the technology_aliases table schema with type safety and validation.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class TechnologyAlias(BaseModel):
    """
    Domain model for technology_aliases table.

    Schema:
        id: Unique identifier (auto-generated)
        technology_id: Reference to technology
        alias: Alias name (unique, max 100 chars)
        created_at: Timestamp when record was created

    Example:
        ```python
        alias = TechnologyAlias(
            id=1,
            technology_id=5,
            alias="py",
            created_at=datetime.now()
        )
        print(alias.alias)  # "py"
        ```
    """

    id: int = Field(..., description="Unique alias identifier")
    technology_id: int = Field(..., description="Technology ID reference")
    alias: str = Field(..., max_length=100, description="Alias name (unique)")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        """Pydantic model configuration."""

        # Allow creating model from ORM objects or dicts
        from_attributes = True

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"TechnologyAlias(id={self.id}, alias='{self.alias}', technology_id={self.technology_id})"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.alias} (ID: {self.id})"
