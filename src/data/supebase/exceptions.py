"""
Custom exception hierarchy for Supabase operations.

This module defines exceptions for error handling throughout the Supabase client.
"""


class SupabaseBaseException(Exception):
    """Base exception for all Supabase-related errors."""

    pass


class SupabaseConfigError(SupabaseBaseException):
    """Configuration validation or initialization errors."""

    pass


class SupabaseConnectionError(SupabaseBaseException):
    """Network or connection-related errors."""

    pass


class SupabaseTimeoutError(SupabaseConnectionError):
    """Request timeout errors."""

    pass


class SupabaseNetworkError(SupabaseConnectionError):
    """Network failure errors."""

    pass


class SupabaseAuthError(SupabaseBaseException):
    """Authentication and authorization errors (401, 403)."""

    pass


class SupabaseNotFoundError(SupabaseBaseException):
    """Resource not found errors (404)."""

    pass


class SupabaseConflictError(SupabaseBaseException):
    """Conflict errors such as unique violations (409)."""

    pass


class SupabaseValidationError(SupabaseBaseException):
    """Data validation errors (400)."""

    pass


class SupabaseRateLimitError(SupabaseBaseException):
    """Rate limiting errors (429)."""

    pass


class SupabaseServerError(SupabaseBaseException):
    """Server errors (500+)."""

    pass


class SupabaseCircuitBreakerError(SupabaseBaseException):
    """Circuit breaker is open, failing fast."""

    pass


class SupabaseRetryExhaustedError(SupabaseBaseException):
    """Maximum retry attempts exceeded."""

    pass
