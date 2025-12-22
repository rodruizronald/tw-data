"""
Job Technology domain model.

Represents the job_technologies table schema with type safety and validation.
This is a junction table linking jobs to technologies.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class JobTechnology(BaseModel):
    """
    Domain model for job_technologies table.

    Schema:
        id: Unique identifier (auto-generated)
        job_id: Reference to job
        technology_id: Reference to technology
        created_at: Timestamp when record was created

    Example:
        ```python
        job_tech = JobTechnology(
            id=1,
            job_id=10,
            technology_id=5,
            created_at=datetime.now()
        )
        print(job_tech.job_id)  # 10
        print(job_tech.technology_id)  # 5
        ```
    """

    id: int = Field(..., description="Unique job technology identifier")
    job_id: int = Field(..., description="Job ID reference")
    technology_id: int = Field(..., description="Technology ID reference")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        """Pydantic model configuration."""

        # Allow creating model from ORM objects or dicts
        from_attributes = True

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"JobTechnology(id={self.id}, job_id={self.job_id}, technology_id={self.technology_id})"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"JobTechnology(job={self.job_id}, tech={self.technology_id})"
