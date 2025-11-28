"""
Supabase client infrastructure for the tw-data project.

This package provides a robust Supabase client with:
- Singleton pattern for connection management
- Retry logic with exponential backoff (tenacity)
- Circuit breaker pattern (pybreaker)
- Comprehensive error handling
- Type-safe CRUD operations
- Structured logging

Public API:
    - SupabaseManager: Singleton for client management
    - BaseTableClient: Base class for table-specific clients
    - Exceptions: All custom exception types
    - Clients: Table-specific client implementations

Example Usage:
    ```python
    from data.supebase import SupabaseManager
    from data.supebase.clients import ExampleTableClient

    # Initialize manager (singleton)
    manager = SupabaseManager()

    # Create table client
    example_client = ExampleTableClient(manager)

    # Perform operations (with automatic retry & circuit breaker)
    try:
        records = example_client.select(filters={"status": "active"})
        new_record = example_client.insert({"name": "Test", "status": "active"})
    except SupabaseException as e:
        logger.error(f"Operation failed: {e}")
    ```
"""

# Core components
from data.supebase.base_client import BaseTableClient
from data.supebase.config import SupabaseConfig, supabase_config

# Decorators (for advanced usage)
from data.supebase.decorators import (
    with_circuit_breaker,
    with_resilience,
    with_retry,
)

# Exceptions
from data.supebase.exceptions import (
    SupabaseAuthError,
    SupabaseBaseException,
    SupabaseCircuitBreakerError,
    SupabaseConfigError,
    SupabaseConflictError,
    SupabaseConnectionError,
    SupabaseNetworkError,
    SupabaseNotFoundError,
    SupabaseRateLimitError,
    SupabaseRetryExhaustedError,
    SupabaseServerError,
    SupabaseTimeoutError,
    SupabaseValidationError,
)
from data.supebase.manager import SupabaseManager, supabase_manager

# Types
from data.supebase.types import FilterDict, RecordDict, ResponseData

__all__ = [
    "BaseTableClient",
    # Types
    "FilterDict",
    "RecordDict",
    "ResponseData",
    "SupabaseAuthError",
    # Exceptions
    "SupabaseBaseException",
    "SupabaseCircuitBreakerError",
    # Configuration
    "SupabaseConfig",
    "SupabaseConfigError",
    "SupabaseConflictError",
    "SupabaseConnectionError",
    # Core
    "SupabaseManager",
    "SupabaseNetworkError",
    "SupabaseNotFoundError",
    "SupabaseRateLimitError",
    "SupabaseRetryExhaustedError",
    "SupabaseServerError",
    "SupabaseTimeoutError",
    "SupabaseValidationError",
    "supabase_config",
    "supabase_manager",
    "with_circuit_breaker",
    "with_resilience",
    # Decorators
    "with_retry",
]

__version__ = "1.0.0"
