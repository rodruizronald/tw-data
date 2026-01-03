"""
Task result models for pipeline execution.

This module provides result containers that distinguish between
successful execution with no data vs. failed execution.
"""

from dataclasses import dataclass
from typing import Self


@dataclass
class TaskResult[T]:
    """Result container for task execution.

    This type allows flows to distinguish between:
    - Success with data: TaskResult(success=True, data=[...])
    - Success with no data: TaskResult(success=True, data=[])
    - Failure: TaskResult(success=False, error="...")

    Attributes:
        success: Whether the task completed without errors
        data: The result data (None if failed)
        error: Error message if failed (None if successful)
        company_name: Name of the company processed
    """

    success: bool
    data: T | None = None
    error: str | None = None
    company_name: str = ""

    @classmethod
    def ok(cls, data: T, company_name: str) -> Self:
        """Create a successful result.

        Args:
            data: The result data
            company_name: Name of the company processed

        Returns:
            TaskResult with success=True and the provided data
        """
        return cls(success=True, data=data, company_name=company_name)

    @classmethod
    def fail(cls, error: str, company_name: str) -> Self:
        """Create a failed result.

        Args:
            error: Error message describing the failure
            company_name: Name of the company that failed

        Returns:
            TaskResult with success=False and the error message
        """
        return cls(success=False, error=error, company_name=company_name)

    @property
    def is_success(self) -> bool:
        """Check if the result represents a successful execution."""
        return self.success

    @property
    def is_failure(self) -> bool:
        """Check if the result represents a failed execution."""
        return not self.success
