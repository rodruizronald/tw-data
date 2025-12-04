"""
Technology domain model.

Represents the technologies table schema with type safety and validation.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class Technology(BaseModel):
    """
    Domain model for technologies table.

    Schema:
        id: Unique identifier (auto-generated)
        name: Technology name (unique, max 100 chars)
        parent_id: Optional reference to parent technology
        created_at: Timestamp when record was created

    Example:
        ```python
        technology = Technology(
            id=1,
            name="Python",
            parent_id=None,
            created_at=datetime.now()
        )
        print(technology.name)  # "Python"
        ```
    """

    id: int = Field(..., description="Unique technology identifier")
    name: str = Field(..., max_length=100, description="Technology name (unique)")
    parent_id: int | None = Field(
        default=None, description="Parent technology ID (optional)"
    )
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        """Pydantic model configuration."""

        # Allow creating model from ORM objects or dicts
        from_attributes = True

    def __repr__(self) -> str:
        """String representation for debugging."""
        parent_info = f", parent_id={self.parent_id}" if self.parent_id else ""
        return f"Technology(id={self.id}, name='{self.name}'{parent_info})"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.name} (ID: {self.id})"
