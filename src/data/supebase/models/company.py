"""
Company domain model.

Represents the companies table schema with type safety and validation.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class Company(BaseModel):
    """
    Domain model for companies table.

    Schema:
        id: Unique identifier (auto-generated)
        name: Company name (unique, max 100 chars)
        is_active: Whether the company is active (soft delete flag)
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated

    Example:
        ```python
        company = Company(
            id=1,
            name="Acme Corp",
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        print(company.name)  # "Acme Corp"
        ```
    """

    id: int = Field(..., description="Unique company identifier")
    name: str = Field(..., max_length=100, description="Company name (unique)")
    is_active: bool = Field(default=True, description="Active status (soft delete)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        """Pydantic model configuration."""

        # Allow creating model from ORM objects or dicts
        from_attributes = True

    def __repr__(self) -> str:
        """String representation for debugging."""
        status = "active" if self.is_active else "inactive"
        return f"Company(id={self.id}, name='{self.name}', status={status})"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.name} (ID: {self.id})"
