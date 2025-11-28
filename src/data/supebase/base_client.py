"""
Abstract base class for Supabase table clients.

This module provides a base implementation for table-specific clients
with common CRUD operations, error handling, retry logic, and circuit breaker.
"""

import logging
from abc import ABC

import httpx
from supabase import Client

from data.supebase.decorators import with_resilience
from data.supebase.exceptions import (
    SupabaseAuthError,
    SupabaseConflictError,
    SupabaseConnectionError,
    SupabaseNetworkError,
    SupabaseNotFoundError,
    SupabaseRateLimitError,
    SupabaseServerError,
    SupabaseTimeoutError,
    SupabaseValidationError,
)
from data.supebase.types import FilterDict, RecordDict, ResponseData

logger = logging.getLogger(__name__)


class BaseTableClient(ABC):  # noqa: B024
    """
    Abstract base class for Supabase table operations.

    Provides common CRUD operations with built-in:
    - Retry logic with exponential backoff
    - Circuit breaker protection
    - Comprehensive error handling
    - Logging and observability
    """

    def __init__(self, client: Client, table_name: str) -> None:
        """
        Initialize table client.

        Args:
            client: Supabase client instance
            table_name: Name of the table to operate on
        """
        self._client = client
        self._table_name = table_name
        self._logger = logging.getLogger(f"{__name__}.{table_name}")
        self._logger.info(f"Initialized table client for: {table_name}")

    @property
    def table_name(self) -> str:
        """Get the table name."""
        return self._table_name

    def _handle_http_error(self, error: httpx.HTTPStatusError) -> None:
        """
        Convert HTTP errors to appropriate Supabase exceptions.

        Args:
            error: The HTTP status error from httpx

        Raises:
            SupabaseAuthError: For 401, 403 errors
            SupabaseNotFoundError: For 404 errors
            SupabaseConflictError: For 409 errors
            SupabaseValidationError: For 400 errors
            SupabaseRateLimitError: For 429 errors
            SupabaseServerError: For 500+ errors
        """
        status_code = error.response.status_code
        error_message = str(error)

        # Try to extract error details from response
        try:
            error_details = error.response.json()
            if isinstance(error_details, dict):
                error_message = error_details.get("message", error_message)
        except Exception:
            pass

        # Map status codes to exceptions
        if status_code in {401, 403}:
            raise SupabaseAuthError(
                f"Authentication failed: {error_message}"
            ) from error
        elif status_code == 404:
            raise SupabaseNotFoundError(
                f"Resource not found: {error_message}"
            ) from error
        elif status_code == 409:
            raise SupabaseConflictError(f"Conflict error: {error_message}") from error
        elif status_code == 400:
            raise SupabaseValidationError(
                f"Validation error: {error_message}"
            ) from error
        elif status_code == 429:
            raise SupabaseRateLimitError(
                f"Rate limit exceeded: {error_message}"
            ) from error
        elif status_code >= 500:
            raise SupabaseServerError(
                f"Server error ({status_code}): {error_message}"
            ) from error
        else:
            # Generic connection error for other status codes
            raise SupabaseConnectionError(
                f"HTTP error ({status_code}): {error_message}"
            ) from error

    def _handle_exception(self, operation: str, error: Exception) -> None:
        """
        Handle exceptions and convert to appropriate Supabase exceptions.

        Args:
            operation: Name of the operation that failed
            error: The exception that was raised

        Raises:
            Various SupabaseException subclasses based on error type
        """
        # Log the error with context
        self._logger.error(
            f"Operation '{operation}' failed on table '{self._table_name}'",
            extra={
                "operation": operation,
                "table": self._table_name,
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
            exc_info=True,
        )

        # Handle HTTP status errors
        if isinstance(error, httpx.HTTPStatusError):
            self._handle_http_error(error)

        # Handle timeout errors
        if isinstance(error, httpx.TimeoutException):
            raise SupabaseTimeoutError(f"Request timeout during {operation}") from error

        # Handle network errors
        if isinstance(error, httpx.NetworkError):
            raise SupabaseNetworkError(
                f"Network error during {operation}: {error}"
            ) from error

        # Re-raise if already a Supabase exception
        if isinstance(
            error,
            (
                SupabaseAuthError,
                SupabaseNotFoundError,
                SupabaseConflictError,
                SupabaseValidationError,
                SupabaseRateLimitError,
                SupabaseServerError,
                SupabaseTimeoutError,
                SupabaseNetworkError,
                SupabaseConnectionError,
            ),
        ):
            raise  # noqa: PLE0704

        # Generic connection error for unknown errors
        raise SupabaseConnectionError(
            f"Unexpected error during {operation}: {error}"
        ) from error

    @with_resilience
    def select(
        self,
        columns: str = "*",
        filters: FilterDict | None = None,
        limit: int | None = None,
        order_by: str | None = None,
        ascending: bool = True,
    ) -> list[RecordDict]:
        """
        Select records from the table.

        Args:
            columns: Columns to select (default: "*")
            filters: Filter conditions as dict (e.g., {"status": "active"})
            limit: Maximum number of records to return
            order_by: Column to order by
            ascending: Sort order (True for ASC, False for DESC)

        Returns:
            List of records matching the criteria

        Raises:
            Various SupabaseException subclasses on errors
        """
        try:
            self._logger.debug(
                f"Selecting from {self._table_name}",
                extra={
                    "columns": columns,
                    "filters": filters,
                    "limit": limit,
                },
            )

            # Build query
            query = self._client.table(self._table_name).select(columns)

            # Apply filters
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)

            # Apply ordering
            if order_by:
                query = query.order(order_by, desc=not ascending)

            # Apply limit
            if limit:
                query = query.limit(limit)

            # Execute query
            response = query.execute()

            self._logger.info(
                f"Selected {len(response.data)} records from {self._table_name}",
                extra={"count": len(response.data)},
            )

            return response.data

        except Exception as e:
            self._handle_exception("select", e)
            raise  # Will never reach here, but keeps type checker happy

    @with_resilience
    def insert(self, data: RecordDict | list[RecordDict]) -> ResponseData:
        """
        Insert one or more records into the table.

        Args:
            data: Record or list of records to insert

        Returns:
            Inserted record(s)

        Raises:
            Various SupabaseException subclasses on errors
        """
        try:
            is_single = isinstance(data, dict)
            record_count = 1 if is_single else len(data)

            self._logger.debug(
                f"Inserting {record_count} record(s) into {self._table_name}",
                extra={"record_count": record_count},
            )

            response = self._client.table(self._table_name).insert(data).execute()

            self._logger.info(
                f"Inserted {record_count} record(s) into {self._table_name}",
                extra={"record_count": record_count},
            )

            return response.data

        except Exception as e:
            self._handle_exception("insert", e)
            raise

    @with_resilience
    def update(self, data: RecordDict, filters: FilterDict) -> ResponseData:
        """
        Update records matching the filters.

        Args:
            data: Data to update
            filters: Filter conditions (e.g., {"id": 123})

        Returns:
            Updated record(s)

        Raises:
            Various SupabaseException subclasses on errors
        """
        try:
            self._logger.debug(
                f"Updating records in {self._table_name}",
                extra={"filters": filters, "data_keys": list(data.keys())},
            )

            # Build query with filters
            query = self._client.table(self._table_name).update(data)
            for key, value in filters.items():
                query = query.eq(key, value)

            response = query.execute()

            record_count = len(response.data) if isinstance(response.data, list) else 1
            self._logger.info(
                f"Updated {record_count} record(s) in {self._table_name}",
                extra={"record_count": record_count},
            )

            return response.data

        except Exception as e:
            self._handle_exception("update", e)
            raise

    @with_resilience
    def delete(self, filters: FilterDict) -> ResponseData:
        """
        Delete records matching the filters.

        Args:
            filters: Filter conditions (e.g., {"id": 123})

        Returns:
            Deleted record(s)

        Raises:
            Various SupabaseException subclasses on errors
        """
        try:
            self._logger.debug(
                f"Deleting records from {self._table_name}",
                extra={"filters": filters},
            )

            # Build query with filters
            query = self._client.table(self._table_name).delete()
            for key, value in filters.items():
                query = query.eq(key, value)

            response = query.execute()

            record_count = len(response.data) if isinstance(response.data, list) else 1
            self._logger.info(
                f"Deleted {record_count} record(s) from {self._table_name}",
                extra={"record_count": record_count},
            )

            return response.data

        except Exception as e:
            self._handle_exception("delete", e)
            raise

    @with_resilience
    def upsert(
        self,
        data: RecordDict | list[RecordDict],
        on_conflict: str | None = None,
    ) -> ResponseData:
        """
        Insert or update records (upsert operation).

        Args:
            data: Record or list of records to upsert
            on_conflict: Column name to use for conflict resolution (optional)

        Returns:
            Upserted record(s)

        Raises:
            Various SupabaseException subclasses on errors

        Note:
            The on_conflict parameter may not be supported in all versions of supabase-py.
            If not supported, the upsert will use the table's primary key for conflict resolution.
        """
        try:
            is_single = isinstance(data, dict)
            record_count = 1 if is_single else len(data)

            self._logger.debug(
                f"Upserting {record_count} record(s) into {self._table_name}",
                extra={"record_count": record_count, "on_conflict": on_conflict},
            )

            query = self._client.table(self._table_name).upsert(data)

            # Try to apply on_conflict if specified and supported
            if on_conflict:
                try:
                    query = query.on_conflict(on_conflict)  # type: ignore[attr-defined]
                except AttributeError:
                    self._logger.warning(
                        "on_conflict not supported, using default conflict resolution",
                        extra={"on_conflict": on_conflict},
                    )

            response = query.execute()

            self._logger.info(
                f"Upserted {record_count} record(s) into {self._table_name}",
                extra={"record_count": record_count},
            )

            return response.data

        except Exception as e:
            self._handle_exception("upsert", e)
            raise
