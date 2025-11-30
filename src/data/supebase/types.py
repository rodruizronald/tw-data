"""
Type definitions and protocols for Supabase client.

This module provides type hints, protocols, and type aliases used throughout
the Supabase client infrastructure.
"""

from typing import Any, Protocol

# Type aliases
type FilterDict = dict[str, Any]
type RecordDict = dict[str, Any]
type ResponseData = list[RecordDict] | RecordDict | None


class SupabaseClientProtocol(Protocol):
    """Protocol defining the interface for Supabase client."""

    def table(self, table_name: str) -> Any:
        """Access a table for operations."""
        ...

    def schema(self, schema_name: str) -> Any:
        """Switch to a different schema."""
        ...


class QueryBuilderProtocol(Protocol):
    """Protocol for Supabase query builder."""

    def select(self, *args: Any, **kwargs: Any) -> Any:
        """Select operation."""
        ...

    def insert(self, *args: Any, **kwargs: Any) -> Any:
        """Insert operation."""
        ...

    def update(self, *args: Any, **kwargs: Any) -> Any:
        """Update operation."""
        ...

    def delete(self, *args: Any, **kwargs: Any) -> Any:
        """Delete operation."""
        ...

    def upsert(self, *args: Any, **kwargs: Any) -> Any:
        """Upsert operation."""
        ...

    def execute(self) -> Any:
        """Execute the query."""
        ...
