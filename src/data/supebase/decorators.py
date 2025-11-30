"""
Decorators for resilience patterns (retry and circuit breaker).

This module provides decorators that implement retry logic with exponential
backoff and circuit breaker pattern to protect against cascading failures.
"""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import httpx
from pybreaker import CircuitBreaker, CircuitBreakerListener
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.config.database import supabase_config
from data.supebase.exceptions import (
    SupabaseCircuitBreakerError,
    SupabaseConnectionError,
    SupabaseNetworkError,
    SupabaseRateLimitError,
    SupabaseRetryExhaustedError,
    SupabaseServerError,
    SupabaseTimeoutError,
)

logger = logging.getLogger(__name__)

# Type variables for generic decorator typing
F = TypeVar("F", bound=Callable[..., Any])


class _CircuitBreakerListener(CircuitBreakerListener):
    """Listener to log circuit breaker state changes."""

    def state_change(self, cb: CircuitBreaker, old_state: Any, new_state: Any) -> None:
        """Called when the circuit breaker state changes."""
        logger.warning(
            f"Circuit breaker state changed to: {new_state}",
            extra={
                "circuit_breaker_state": str(new_state),
                "old_state": str(old_state),
                "failure_count": cb.fail_counter,
                "fail_max": cb.fail_max,
            },
        )


# Global circuit breaker instance (shared across all operations)
circuit_breaker = CircuitBreaker(
    fail_max=supabase_config.supabase_cb_failure_threshold,
    reset_timeout=supabase_config.supabase_cb_recovery_timeout,
    exclude=[
        # Don't count these as failures for circuit breaker
        SupabaseCircuitBreakerError,
    ],
    listeners=list[CircuitBreakerListener]([_CircuitBreakerListener()]),
)


def _should_retry_exception(exception: BaseException) -> bool:
    """
    Determine if an exception should trigger a retry.

    Args:
        exception: The exception that was raised

    Returns:
        bool: True if should retry, False otherwise
    """
    # Retry on network/connection errors
    if isinstance(
        exception,
        (
            SupabaseTimeoutError,
            SupabaseNetworkError,
            SupabaseConnectionError,
            SupabaseServerError,
            SupabaseRateLimitError,
        ),
    ):
        return True

    # Retry on specific HTTP status codes via httpx
    if isinstance(exception, httpx.HTTPStatusError):
        status_code = exception.response.status_code
        # Retry on 429 (rate limit), 500, 502, 503, 504
        if status_code in {429, 500, 502, 503, 504}:
            return True

    # Retry on httpx timeouts and network errors
    return bool(isinstance(exception, (httpx.TimeoutException, httpx.NetworkError)))


def with_retry[F: Callable[..., Any]](func: F) -> F:
    """
    Decorator to add retry logic with exponential backoff to a function.

    The retry behavior is configured via SupabaseConfig settings:
    - max_retries: Maximum number of retry attempts
    - retry_min_wait: Minimum wait time between retries (seconds)
    - retry_max_wait: Maximum wait time between retries (seconds)
    - retry_multiplier: Exponential backoff multiplier

    Args:
        func: The function to wrap with retry logic

    Returns:
        Wrapped function with retry logic
    """
    config = supabase_config

    @retry(
        retry=retry_if_exception_type(
            (
                SupabaseTimeoutError,
                SupabaseNetworkError,
                SupabaseConnectionError,
                SupabaseServerError,
                SupabaseRateLimitError,
                httpx.TimeoutException,
                httpx.NetworkError,
            )
        ),
        stop=stop_after_attempt(config.supabase_max_retries),
        wait=wait_exponential(
            multiplier=config.supabase_retry_multiplier,
            min=config.supabase_retry_min_wait,
            max=config.supabase_retry_max_wait,
        ),
        reraise=True,
    )
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Log the final failure after all retries exhausted
            logger.error(
                f"Function {func.__name__} failed after {config.supabase_max_retries} retries",
                extra={
                    "function": func.__name__,
                    "max_retries": config.supabase_max_retries,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            # Wrap in SupabaseRetryExhaustedError if it was a retryable error
            if _should_retry_exception(e):
                raise SupabaseRetryExhaustedError(
                    f"Max retries ({config.supabase_max_retries}) exceeded"
                ) from e
            raise

    return wrapper  # type: ignore[return-value]


def with_circuit_breaker[F: Callable[..., Any]](func: F) -> F:
    """
    Decorator to add circuit breaker pattern to a function.

    The circuit breaker protects against cascading failures by:
    - Opening after consecutive failures exceed threshold
    - Failing fast when open (without attempting the operation)
    - Allowing a test request after recovery timeout (half-open state)
    - Closing if the test request succeeds

    Args:
        func: The function to wrap with circuit breaker

    Returns:
        Wrapped function with circuit breaker protection
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            # Circuit breaker will raise CircuitBreakerOpen if open
            return circuit_breaker.call(func, *args, **kwargs)
        except Exception as e:
            # If circuit breaker is open, raise our custom exception
            if "CircuitBreakerOpen" in type(e).__name__:
                logger.error(
                    f"Circuit breaker is OPEN - failing fast for {func.__name__}",
                    extra={
                        "function": func.__name__,
                        "circuit_breaker_state": "open",
                    },
                )
                raise SupabaseCircuitBreakerError(
                    "Circuit breaker is open - service unavailable"
                ) from e
            raise

    return wrapper  # type: ignore[return-value]


def with_resilience[F: Callable[..., Any]](func: F) -> F:
    """
    Combined decorator applying both retry and circuit breaker patterns.

    This decorator combines:
    1. Circuit breaker (outer) - fails fast if circuit is open
    2. Retry logic (inner) - retries on transient failures

    Order matters: Circuit breaker wraps retry logic so that:
    - If circuit is open, we fail immediately without retrying
    - If circuit is closed, we attempt with retries
    - Consecutive retry failures count toward circuit breaker threshold

    Args:
        func: The function to wrap with resilience patterns

    Returns:
        Wrapped function with both retry and circuit breaker
    """
    # Apply decorators in order: retry first (inner), then circuit breaker (outer)
    retried_func = with_retry(func)
    return with_circuit_breaker(retried_func)
