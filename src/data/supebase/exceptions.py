"""
Custom exception hierarchy for Supabase operations.

This module defines exceptions for error handling throughout the Supabase client.
"""


class SupabaseBaseException(Exception):
    """Base exception for all Supabase-related errors.

    Attributes:
        retryable: Class-level flag indicating if this error type is transient
                   and may succeed on retry. Subclasses should override this.
    """

    retryable: bool = False  # Default to non-retryable


class SupabaseConfigError(SupabaseBaseException):
    """Configuration validation or initialization errors."""

    pass


class SupabaseConnectionError(SupabaseBaseException):
    """Network or connection-related errors.

    Retryable because network issues are typically transient.
    """

    retryable = True


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
    """Rate limiting errors (429).

    Retryable because rate limits will succeed after backoff.
    """

    retryable = True


class SupabaseServerError(SupabaseBaseException):
    """Server errors (500+).

    Retryable because server errors are typically transient.
    """

    retryable = True


class SupabaseCircuitBreakerError(SupabaseBaseException):
    """Circuit breaker is open, failing fast."""

    pass


class SupabaseRetryExhaustedError(SupabaseBaseException):
    """Maximum retry attempts exceeded."""

    pass
