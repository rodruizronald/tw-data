"""
Database connection controller for MongoDB.

This module handles MongoDB connection management, configuration,
and provides a centralized database controller following best practices.
"""

import logging
from typing import Any, Optional

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from core.config.database import get_database_config

logger = logging.getLogger(__name__)


class DatabaseController:
    """
    MongoDB database controller implementing singleton pattern.

    Provides synchronous database connections with proper connection
    pooling and error handling.
    """

    _instance: Optional["DatabaseController"] = None

    def __new__(cls) -> "DatabaseController":
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize database controller with configuration from DatabaseConfig."""
        if hasattr(self, "_initialized"):
            return

        # Initialize instance variables
        self._client: MongoClient[Any] | None = None
        self._config = get_database_config()

        self._initialized: bool = True
        logger.info(
            f"Database controller initialized for database: {self._config.database}"
        )

    def get_client(self) -> MongoClient[Any]:
        """
        Get MongoDB client.

        Returns:
            MongoClient: Configured MongoDB client

        Raises:
            ConnectionFailure: If unable to connect to MongoDB
        """
        if self._client is None:
            try:
                # Use connection string from config or build it
                connection_string = (
                    self._config.connection_string
                    if self._config.connection_string
                    else self._config.build_connection_string()
                )

                # Explicit type annotation for clarity
                client: MongoClient[Any] = MongoClient(
                    connection_string,
                    connectTimeoutMS=self._config.connection_timeout,
                    serverSelectionTimeoutMS=self._config.server_selection_timeout,
                )
                # Test connection
                client.admin.command("ping")
                self._client = client
                logger.info("Successfully connected to MongoDB")
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                raise ConnectionFailure(f"Unable to connect to MongoDB: {e}") from e

        return self._client

    def get_database(self) -> Database[Any]:
        """
        Get database instance.

        Returns:
            Database: Database instance
        """
        client = self.get_client()
        return client[self._config.database]

    def close_connections(self) -> None:
        """Close all database connections."""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("MongoDB connection closed")


# Global database controller instance
db_controller = DatabaseController()
