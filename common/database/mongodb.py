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
"""

from typing import List, Type, Optional
from beanie import init_beanie, Document
from motor.motor_asyncio import AsyncIOMotorClient


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
        self._client = AsyncIOMotorClient(uri)
        self._database_name = database_name

        await init_beanie(
            database=self._client[database_name],
            document_models=document_models,
        )
        self._initialized = True

    async def disconnect(self) -> None:
        """Close the MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._database_name = None
            self._initialized = False

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

    def get_collection(self, name: str):
        """
        Get a raw Motor collection for direct access.

        Useful for operations not covered by Beanie, like aggregations.
        """
        if not self._client or not self._database_name:
            raise RuntimeError("Database not connected")
        return self._client[self._database_name][name]
