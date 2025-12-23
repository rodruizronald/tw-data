"""
Configuration settings for the data layer.

This module provides configuration management for database connections
and data layer settings.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load environment variables when this module is imported
# Try to find .env file in current directory or parent directories
current_dir = Path.cwd()
for parent in [current_dir, *list(current_dir.parents)]:
    env_path = parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        break


@dataclass
class DatabaseConfig:
    """Database configuration settings."""

    # Connection settings
    host: str = field(default_factory=lambda: os.getenv("MONGO_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("MONGO_PORT", "27017")))
    username: str | None = field(default_factory=lambda: os.getenv("MONGO_USERNAME"))
    password: str | None = field(default_factory=lambda: os.getenv("MONGO_PASSWORD"))
    database: str = field(
        default_factory=lambda: os.getenv("MONGO_DATABASE", "job_scraper")
    )
    auth_source: str = field(
        default_factory=lambda: os.getenv("MONGO_AUTH_SOURCE", "admin")
    )

    # Connection string (if provided, overrides individual settings)
    connection_string: str | None = field(
        default_factory=lambda: os.getenv("MONGO_CONNECTION_STRING")
    )

    # Timeout settings (in milliseconds)
    connection_timeout: int = field(
        default_factory=lambda: int(os.getenv("MONGO_CONNECTION_TIMEOUT", "5000"))
    )
    server_selection_timeout: int = field(
        default_factory=lambda: int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT", "5000"))
    )

    # Collection names
    job_listings_collection: str = field(
        default_factory=lambda: os.getenv(
            "MONGO_JOB_LISTINGS_COLLECTION", "job_listings"
        )
    )

    # Job metrics collections
    job_metrics_daily_collection: str = field(
        default_factory=lambda: os.getenv(
            "MONGO_JOB_METRICS_DAILY_COLLECTION", "job_metrics_daily"
        )
    )
    job_metrics_aggregates_collection: str = field(
        default_factory=lambda: os.getenv(
            "MONGO_JOB_METRICS_AGGREGATES_COLLECTION", "job_metrics_aggregates"
        )
    )

    # Unmatched technologies collection
    unmatched_technologies_collection: str = field(
        default_factory=lambda: os.getenv(
            "MONGO_UNMATCHED_TECHNOLOGIES_COLLECTION", "unmatched_technologies"
        )
    )

    def build_connection_string(self) -> str:
        """Build MongoDB connection string from configuration."""
        if self.connection_string:
            return self.connection_string

        if self.username and self.password:
            # Include the database name in the connection string
            return f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}?authSource={self.auth_source}"
        else:
            return f"mongodb://{self.host}:{self.port}/{self.database}"

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "connection_string": self.build_connection_string(),
            "connection_timeout": self.connection_timeout,
            "server_selection_timeout": self.server_selection_timeout,
            "job_listings_collection": self.job_listings_collection,
            "job_metrics_daily_collection": self.job_metrics_daily_collection,
            "job_metrics_aggregates_collection": self.job_metrics_aggregates_collection,
            "unmatched_technologies_collection": self.unmatched_technologies_collection,
        }


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
mongodb_config = DatabaseConfig()
