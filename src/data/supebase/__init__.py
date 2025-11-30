"""
Supabase data infrastructure for the tw-data project.

This package provides a robust Supabase data layer with:
- Singleton pattern for connection management
- Retry logic with exponential backoff (tenacity)
- Circuit breaker pattern (pybreaker)
- Comprehensive error handling
- Type-safe CRUD operations
- Structured logging
- Repository pattern for data access

Public API:
    - SupabaseManager: Singleton for client management
    - BaseRepository: Base class for table-specific repositories
    - Exceptions: All custom exception types
    - Repositories: Table-specific repository implementations

Example Usage:
    ```python
    from data.supebase import SupabaseManager
    from data.supebase.repositories import CompaniesRepository

    # Initialize manager (singleton)
    manager = SupabaseManager()

    # Create repository
    companies_repo = CompaniesRepository(manager.client)

    # Perform operations (with automatic retry & circuit breaker)
    try:
        companies = companies_repo.get_active()
        new_company = companies_repo.create(name="Acme Corp")
    except SupabaseException as e:
        logger.error(f"Operation failed: {e}")
    ```
"""

# Core components
from data.supebase.base_repository import BaseRepository

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

# Models
from data.supebase.models import Company

# Repositories
from data.supebase.repositories import CompaniesRepository

# Types
from data.supebase.types import FilterDict, RecordDict, ResponseData

__all__ = [
    "BaseRepository",
    "CompaniesRepository",
    "Company",
    "FilterDict",
    "RecordDict",
    "ResponseData",
    "SupabaseAuthError",
    "SupabaseBaseException",
    "SupabaseCircuitBreakerError",
    "SupabaseConfigError",
    "SupabaseConflictError",
    "SupabaseConnectionError",
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
    "with_retry",
]

__version__ = "1.0.0"
