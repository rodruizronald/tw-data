"""
Repository layer for unmatched technology CRUD operations.

This module provides the repository pattern implementation for UnmatchedTechnology
with comprehensive CRUD operations and business logic methods.
"""

import logging
from typing import Any

from bson import ObjectId
from pymongo.errors import PyMongoError

from core.config.database import mongodb_config
from data.mongo.controller import DatabaseController
from data.mongo.models.unmatched_technology import UnmatchedTechnology
from data.mongo.repositories.base_repo import BaseRepository

logger = logging.getLogger(__name__)


class UnmatchedTechnologyRepository(BaseRepository[UnmatchedTechnology]):
    """
    Repository for UnmatchedTechnology CRUD operations following repository pattern.

    Provides high-level database operations with error handling, logging,
    and business logic encapsulation.
    """

    def __init__(self, db_controller: DatabaseController) -> None:
        super().__init__(
            db_controller, mongodb_config.unmatched_technologies_collection
        )

    # Implement abstract methods
    def _to_dict(self, model: UnmatchedTechnology) -> dict[str, Any]:
        """Convert model to dictionary for storage."""
        result: dict[str, Any] = model.to_dict()
        return result

    def _from_dict(self, data: dict[str, Any]) -> UnmatchedTechnology:
        return UnmatchedTechnology.from_dict(data)

    def _get_unique_key(self, model: UnmatchedTechnology) -> str:
        """Get unique identifier for logging."""
        name: str = model.name
        return name

    def _get_id(self, model: UnmatchedTechnology) -> ObjectId | None:
        """Get MongoDB _id from model."""
        _id: ObjectId | None = model._id
        return _id

    def _set_id(self, model: UnmatchedTechnology, object_id: ObjectId) -> None:
        model._id = object_id

    # Domain-specific methods
    def get_by_name(self, name: str) -> UnmatchedTechnology | None:
        """
        Retrieve unmatched technology by name.

        Args:
            name: Technology name

        Returns:
            UnmatchedTechnology: Found unmatched technology or None
        """
        try:
            doc = self.collection.find_one({"name": name})
            if doc:
                return UnmatchedTechnology.from_dict(doc)
            return None
        except PyMongoError as e:
            logger.error(f"Error retrieving unmatched technology by name {name}: {e}")
            return None

    def exists_by_name(self, name: str) -> bool:
        """
        Check if an unmatched technology exists by name.

        Args:
            name: Technology name

        Returns:
            bool: True if exists, False otherwise
        """
        try:
            count: int = self.collection.count_documents({"name": name})
            return count > 0
        except PyMongoError as e:
            logger.error(
                f"Error checking if unmatched technology exists by name {name}: {e}"
            )
            return False

    def create_if_not_exists(self, name: str) -> UnmatchedTechnology | None:
        """
        Create an unmatched technology entry if it doesn't already exist.

        Args:
            name: Technology name

        Returns:
            UnmatchedTechnology: Created or existing unmatched technology, or None on error
        """
        try:
            # Check if already exists
            existing = self.get_by_name(name)
            if existing:
                logger.debug(f"Unmatched technology already exists: {name}")
                return existing

            # Create new entry
            unmatched_tech = UnmatchedTechnology(name=name)
            return self.create(unmatched_tech)

        except PyMongoError as e:
            logger.error(f"Error creating unmatched technology {name}: {e}")
            return None

    def delete_by_name(self, name: str) -> bool:
        """
        Delete unmatched technology by name.

        Args:
            name: Technology name

        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            result = self.collection.delete_one({"name": name})

            if result.deleted_count > 0:
                logger.info(f"Deleted unmatched technology: {name}")
                return True
            else:
                logger.warning(f"No unmatched technology found with name: {name}")
                return False

        except PyMongoError as e:
            logger.error(f"Error deleting unmatched technology {name}: {e}")
            return False

    def get_all_names(self) -> list[str]:
        """
        Get all unmatched technology names.

        Returns:
            list[str]: List of all unmatched technology names
        """
        try:
            cursor = self.collection.find({}, {"name": 1, "_id": 0})
            return [doc["name"] for doc in cursor]
        except PyMongoError as e:
            logger.error(f"Error getting all unmatched technology names: {e}")
            return []
