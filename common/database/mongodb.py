"""
Generic MongoDB connection manager using Beanie ODM.

This module provides async MongoDB connectivity that works with any database.
Models are provided at connection time, allowing complete separation of
database infrastructure from application-specific schemas.

Example:
    from common.database import MongoDB
    from app.models import User, CheckIn

    db = MongoDB()
    await db.connect(
        uri="mongodb://localhost:27017",
        database_name="myapp",
        document_models=[User, CheckIn]
    )

Singleton access:
    from common.database.mongodb import get_main_database, get_hub_database

    # Get database instances
    main_db = get_main_database()
    hub_db = get_hub_database()

    # Get collections via get_collection()
    users = main_db.get_collection("users")
"""

import logging
from typing import List, Type, Optional

from beanie import init_beanie, Document
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# Singleton database instances
# ─────────────────────────────────────────────────────────────────

_main_database: Optional["MongoDB"] = None
_hub_database: Optional["MongoDB"] = None


class MongoDB:
    """Generic MongoDB connection manager - works with any database."""

    def __init__(self):
        self._client: Optional[AsyncIOMotorClient] = None
        self._database_name: Optional[str] = None
        self._initialized: bool = False

    async def connect(
        self,
        uri: str,
        database_name: str,
        document_models: List[Type[Document]],
    ) -> None:
        """
        Connect to MongoDB and initialize Beanie with provided models.

        Args:
            uri: MongoDB connection string
            database_name: Name of the database to use
            document_models: List of Beanie Document classes to initialize
        """
        # Mask the URI for logging (hide credentials)
        masked_uri = uri.split("@")[-1] if "@" in uri else uri
        logger.info(f"Connecting to MongoDB: {masked_uri}")
        logger.debug(f"Database name: {database_name}")
        logger.debug(f"Document models: {[m.__name__ for m in document_models]}")

        try:
            self._client = AsyncIOMotorClient(uri)
            self._database_name = database_name

            logger.debug("Initializing Beanie ODM")
            await init_beanie(
                database=self._client[database_name],
                document_models=document_models,
            )
            self._initialized = True
            logger.info(f"Successfully connected to MongoDB database: {database_name}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def disconnect(self) -> None:
        """Close the MongoDB connection."""
        if self._client:
            logger.info(f"Disconnecting from MongoDB database: {self._database_name}")
            self._client.close()
            self._client = None
            self._database_name = None
            self._initialized = False
            logger.debug("MongoDB connection closed")

    @property
    def is_connected(self) -> bool:
        """Check if database is connected and initialized."""
        return self._initialized

    @property
    def client(self) -> Optional[AsyncIOMotorClient]:
        """Get the underlying Motor client."""
        return self._client

    @property
    def database_name(self) -> Optional[str]:
        """Get the current database name."""
        return self._database_name

    @property
    def db(self) -> AsyncIOMotorDatabase:
        """Get the underlying Motor database instance."""
        if not self._client or not self._database_name:
            raise RuntimeError("Database not connected")
        return self._client[self._database_name]

    def get_collection(self, name: str):
        """
        Get a raw Motor collection for direct access.

        Useful for operations not covered by Beanie, like aggregations.

        Args:
            name: Collection name

        Returns:
            AsyncIOMotorCollection instance
        """
        if not self._client or not self._database_name:
            logger.error("Attempted to get collection without database connection")
            raise RuntimeError("Database not connected")
        logger.debug(f"Getting collection: {name}")
        return self._client[self._database_name][name]


# ─────────────────────────────────────────────────────────────────
# Singleton initialization and getters
# ─────────────────────────────────────────────────────────────────

def set_main_database(db: "MongoDB") -> None:
    """
    Set the main database singleton from an existing MongoDB instance.

    Args:
        db: MongoDB instance to use as main database
    """
    global _main_database
    _main_database = db
    logger.info("Main database singleton set")


def set_hub_database(db: "MongoDB") -> None:
    """
    Set the hub database singleton from an existing MongoDB instance.

    Args:
        db: MongoDB instance to use as hub database
    """
    global _hub_database
    _hub_database = db
    logger.info("Hub database singleton set")


def get_main_database() -> "MongoDB":
    """
    Get the main application database singleton.

    Returns:
        MongoDB instance

    Raises:
        RuntimeError: If database not initialized
    """
    if _main_database is None:
        raise RuntimeError("Main database not initialized. Call set_main_database() first.")
    return _main_database


def get_hub_database() -> "MongoDB":
    """
    Get the hub database singleton.

    Returns:
        MongoDB instance

    Raises:
        RuntimeError: If database not initialized
    """
    if _hub_database is None:
        raise RuntimeError("Hub database not initialized. Call set_hub_database() first.")
    return _hub_database
