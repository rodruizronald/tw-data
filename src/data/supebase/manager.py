"""
Supabase connection manager implementing singleton pattern.

This module handles Supabase client initialization, configuration,
and provides centralized client management.
"""

import logging
from typing import Any

from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from core.config.database import supabase_config
from data.supebase.exceptions import SupabaseConfigError, SupabaseConnectionError

logger = logging.getLogger(__name__)


class SupabaseManager:
    """
    Supabase client manager implementing singleton pattern.

    Provides synchronous Supabase client with proper configuration,
    connection management, and error handling.
    """

    _instance: "SupabaseManager | None" = None

    def __new__(cls) -> "SupabaseManager":
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize Supabase manager with configuration."""
        if hasattr(self, "_initialized"):
            return

        # Initialize instance variables
        self._client: Client | None = None
        try:
            self._config = supabase_config
        except Exception as e:
            logger.error(f"Failed to load Supabase configuration: {e}")
            raise SupabaseConfigError(f"Invalid Supabase configuration: {e}") from e

        self._initialized: bool = True
        logger.info(
            "Supabase manager initialized",
            extra={
                "url": self._config.supabase_url,
                "schema": self._config.supabase_schema,
            },
        )

    def get_client(self) -> Client:
        """
        Get or create Supabase client instance.

        Returns:
            Client: Configured Supabase client

        Raises:
            SupabaseConnectionError: If unable to create client
            SupabaseConfigError: If configuration is invalid
        """
        if self._client is None:
            try:
                logger.info("Creating new Supabase client connection")

                # Configure client options for synchronous client
                options = SyncClientOptions(
                    schema=self._config.supabase_schema,
                    postgrest_client_timeout=self._config.supabase_timeout,
                    storage_client_timeout=self._config.supabase_timeout,
                    # Server-side auth configuration (for service role)
                    auto_refresh_token=False,
                    persist_session=False,
                )

                # Create client with service role key (admin access)
                self._client = create_client(
                    supabase_url=self._config.supabase_url,
                    supabase_key=self._config.supabase_service_key,
                    options=options,
                )

                logger.info(
                    "Successfully created Supabase client",
                    extra={
                        "schema": self._config.supabase_schema,
                        "timeout": self._config.supabase_timeout,
                    },
                )

            except Exception as e:
                logger.error(
                    f"Failed to create Supabase client: {e}",
                    exc_info=True,
                )
                raise SupabaseConnectionError(
                    f"Unable to create Supabase client: {e}"
                ) from e

        return self._client

    def close_connections(self) -> None:
        """
        Close all Supabase connections and cleanup resources.

        Note: The Supabase Python client doesn't have an explicit close method,
        but we reset the client instance to allow garbage collection.
        """
        if self._client:
            self._client = None
            logger.info("Supabase client connection reset")

    @property
    def config(self) -> Any:
        """Get the current configuration."""
        return self._config


# Global Supabase manager instance
supabase_manager = SupabaseManager()
