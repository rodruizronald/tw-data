"""
Configuration settings for Supabase client.

This module provides configuration management for Supabase connections
using environment variables.
"""

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SupabaseConfig:
    """Supabase configuration settings with validation."""

    # Required settings
    supabase_url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    supabase_service_key: str = field(
        default_factory=lambda: os.getenv("SUPABASE_SERVICE_KEY", "")
    )

    # Optional settings
    supabase_anon_key: str | None = field(
        default_factory=lambda: os.getenv("SUPABASE_ANON_KEY")
    )
    supabase_schema: str = field(
        default_factory=lambda: os.getenv("SUPABASE_SCHEMA", "public")
    )

    # Timeout configuration (in seconds)
    supabase_timeout: int = field(
        default_factory=lambda: int(os.getenv("SUPABASE_TIMEOUT", "10"))
    )
    supabase_connect_timeout: int = field(
        default_factory=lambda: int(os.getenv("SUPABASE_CONNECT_TIMEOUT", "5"))
    )
    supabase_read_timeout: int = field(
        default_factory=lambda: int(os.getenv("SUPABASE_READ_TIMEOUT", "10"))
    )

    # Retry configuration (tenacity)
    supabase_max_retries: int = field(
        default_factory=lambda: int(os.getenv("SUPABASE_MAX_RETRIES", "3"))
    )
    supabase_retry_min_wait: int = field(
        default_factory=lambda: int(os.getenv("SUPABASE_RETRY_MIN_WAIT", "1"))
    )
    supabase_retry_max_wait: int = field(
        default_factory=lambda: int(os.getenv("SUPABASE_RETRY_MAX_WAIT", "10"))
    )
    supabase_retry_multiplier: int = field(
        default_factory=lambda: int(os.getenv("SUPABASE_RETRY_MULTIPLIER", "2"))
    )

    # Circuit breaker configuration (pybreaker)
    supabase_cb_failure_threshold: int = field(
        default_factory=lambda: int(os.getenv("SUPABASE_CB_FAILURE_THRESHOLD", "5"))
    )
    supabase_cb_recovery_timeout: int = field(
        default_factory=lambda: int(os.getenv("SUPABASE_CB_RECOVERY_TIMEOUT", "60"))
    )

    def __post_init__(self) -> None:
        """Perform validation after initialization."""
        # Validate URL
        if not self.supabase_url:
            raise ValueError("Supabase URL is required (SUPABASE_URL)")
        if not self.supabase_url.startswith(("http://", "https://")):
            raise ValueError("Supabase URL must start with http:// or https://")
        self.supabase_url = self.supabase_url.rstrip("/")

        # Validate service key
        if not self.supabase_service_key or not self.supabase_service_key.strip():
            raise ValueError("Supabase service key is required (SUPABASE_SERVICE_KEY)")

        # Validate retry waits
        if self.supabase_retry_max_wait <= self.supabase_retry_min_wait:
            raise ValueError("retry_max_wait must be greater than retry_min_wait")

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary (excluding sensitive data)."""
        return {
            "url": self.supabase_url,
            "schema": self.supabase_schema,
            "timeout": self.supabase_timeout,
            "connect_timeout": self.supabase_connect_timeout,
            "read_timeout": self.supabase_read_timeout,
            "max_retries": self.supabase_max_retries,
            "retry_min_wait": self.supabase_retry_min_wait,
            "retry_max_wait": self.supabase_retry_max_wait,
            "retry_multiplier": self.supabase_retry_multiplier,
            "cb_failure_threshold": self.supabase_cb_failure_threshold,
            "cb_recovery_timeout": self.supabase_cb_recovery_timeout,
        }


# Global configuration instance
supabase_config = SupabaseConfig()
