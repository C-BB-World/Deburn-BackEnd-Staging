"""
Database module - Generic async MongoDB connection using Beanie ODM.

Provides reusable MongoDB connectivity for any project.

Usage:
    from common.database import MongoDB, get_main_database

    # Set up singleton
    db = MongoDB()
    await db.connect(uri, database_name, models)
    set_main_database(db)

    # Access anywhere
    main_db = get_main_database()
    collection = main_db.get_collection("users")
"""

from common.database.mongodb import (
    MongoDB,
    # Singleton management
    set_main_database,
    set_hub_database,
    get_main_database,
    get_hub_database,
)
from common.database.base_document import BaseDocument

__all__ = [
    "MongoDB",
    "BaseDocument",
    # Singleton management
    "set_main_database",
    "set_hub_database",
    "get_main_database",
    "get_hub_database",
]
