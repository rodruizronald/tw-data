import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from bson import ObjectId
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from data.mongo.controller import DatabaseController

if TYPE_CHECKING:
    from pymongo.results import DeleteResult, InsertOneResult, UpdateResult

logger = logging.getLogger(__name__)


class BaseRepository[T](ABC):
    """
    Generic base repository with common CRUD operations.

    Each feature repository extends this to add domain-specific logic.
    """

    def __init__(self, db_controller: DatabaseController, collection_name: str) -> None:
        """
        Initialize repository.

        Args:
            db_controller: Database controller instance
            collection_name: Name of MongoDB collection
        """
        self.db_controller = db_controller
        self.collection_name = collection_name
        self._collection: Collection | None = None

    @property
    def collection(self) -> Collection:
        """Get MongoDB collection with lazy initialization."""
        if self._collection is None:
            db = self.db_controller.get_database()
            self._collection = db[self.collection_name]
        return self._collection

    @abstractmethod
    def _to_dict(self, model: T) -> dict[str, Any]:
        """Convert model to dictionary for storage."""
        pass

    @abstractmethod
    def _from_dict(self, data: dict[str, Any]) -> T:
        """Convert dictionary to model."""
        pass

    @abstractmethod
    def _get_unique_key(self, model: T) -> str:
        """Get unique identifier for logging."""
        pass

    @abstractmethod
    def _get_id(self, model: T) -> ObjectId | None:
        """Get MongoDB _id from model."""
        pass

    @abstractmethod
    def _set_id(self, model: T, object_id: ObjectId) -> None:
        """Set MongoDB _id on model."""
        pass

    def create(self, model: T) -> T | None:
        """Create a new document."""
        try:
            doc = self._to_dict(model)
            doc.pop("_id", None)

            result: InsertOneResult = self.collection.insert_one(doc)

            if result.inserted_id:
                self._set_id(model, result.inserted_id)
                logger.info(
                    f"Created {self.collection_name}: {self._get_unique_key(model)}"
                )
                return model
            return None

        except DuplicateKeyError:
            logger.warning(
                f"{self.collection_name} already exists: {self._get_unique_key(model)}"
            )
            return None
        except PyMongoError as e:
            logger.error(f"Error creating {self.collection_name}: {e}")
            return None

    def get_by_id(self, object_id: ObjectId) -> T | None:
        """Retrieve document by MongoDB _id."""
        try:
            doc = self.collection.find_one({"_id": object_id})
            return self._from_dict(doc) if doc else None
        except PyMongoError as e:
            logger.error(f"Error retrieving {self.collection_name}: {e}")
            return None

    def update(self, model: T) -> bool:
        """Update existing document."""
        try:
            object_id = self._get_id(model)
            if not object_id:
                logger.error(f"Cannot update {self.collection_name} without _id")
                return False

            doc = self._to_dict(model)
            doc.pop("_id", None)

            result: UpdateResult = self.collection.update_one(
                {"_id": object_id}, {"$set": doc}
            )

            if result.modified_count > 0:
                logger.info(
                    f"Updated {self.collection_name}: {self._get_unique_key(model)}"
                )
                return True
            return False

        except PyMongoError as e:
            logger.error(f"Error updating {self.collection_name}: {e}")
            return False

    def delete_by_id(self, object_id: ObjectId) -> bool:
        """Delete document by _id."""
        try:
            result: DeleteResult = self.collection.delete_one({"_id": object_id})
            return result.deleted_count > 0
        except PyMongoError as e:
            logger.error(f"Error deleting {self.collection_name}: {e}")
            return False

    def count_all(self) -> int:
        """Count total documents."""
        try:
            return self.collection.count_documents({})
        except PyMongoError as e:
            logger.error(f"Error counting {self.collection_name}: {e}")
            return 0

    def find_all(self, limit: int = 100, skip: int = 0) -> list[T]:
        """Find all documents with pagination."""
        try:
            cursor = self.collection.find().skip(skip).limit(limit)
            return [self._from_dict(doc) for doc in cursor]
        except PyMongoError as e:
            logger.error(f"Error finding {self.collection_name}: {e}")
            return []
