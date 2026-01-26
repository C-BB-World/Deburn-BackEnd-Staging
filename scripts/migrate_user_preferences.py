#!/usr/bin/env python3
"""
Migration script to create default preferences for existing users.

This script:
1. Finds all users in the 'users' collection
2. Checks if they have a document in 'userpreferences' collection
3. Creates default preferences for users who don't have one

Usage:
    python scripts/migrate_user_preferences.py

Environment variables required:
    MONGODB_URI - MongoDB connection string
    MONGODB_DATABASE - Database name (default: deburn)
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Default preferences
DEFAULT_COACH_PREFERENCES = {
    "voice": "Alice"
}


async def migrate_preferences():
    """Migrate preferences for all existing users."""

    # Connect to MongoDB
    mongodb_uri = os.getenv("MONGODB_URI")
    database_name = os.getenv("MONGODB_DATABASE", "deburn")

    if not mongodb_uri:
        print("ERROR: MONGODB_URI environment variable not set")
        sys.exit(1)

    print(f"Connecting to database: {database_name}")
    client = AsyncIOMotorClient(mongodb_uri)
    db = client[database_name]

    users_collection = db["users"]
    preferences_collection = db["userpreferences"]

    # Get all user IDs
    print("Fetching all users...")
    users_cursor = users_collection.find({}, {"_id": 1, "email": 1})
    users = await users_cursor.to_list(length=None)
    print(f"Found {len(users)} users")

    # Get all existing preference user IDs
    print("Fetching existing preferences...")
    existing_prefs_cursor = preferences_collection.find({}, {"userId": 1})
    existing_prefs = await existing_prefs_cursor.to_list(length=None)
    existing_user_ids = {doc["userId"] for doc in existing_prefs}
    print(f"Found {len(existing_user_ids)} existing preference documents")

    # Find users without preferences
    users_without_prefs = [
        user for user in users
        if user["_id"] not in existing_user_ids
    ]
    print(f"Found {len(users_without_prefs)} users without preferences")

    if not users_without_prefs:
        print("All users already have preferences. Nothing to migrate.")
        client.close()
        return

    # Create default preferences for users without them
    now = datetime.now(timezone.utc)
    documents_to_insert = []

    for user in users_without_prefs:
        documents_to_insert.append({
            "userId": user["_id"],
            "coachPreferences": DEFAULT_COACH_PREFERENCES.copy(),
            "createdAt": now,
            "updatedAt": now
        })

    print(f"Creating {len(documents_to_insert)} preference documents...")
    result = await preferences_collection.insert_many(documents_to_insert)
    print(f"Successfully created {len(result.inserted_ids)} preference documents")

    # Print summary
    print("\n" + "=" * 50)
    print("Migration Summary")
    print("=" * 50)
    print(f"Total users: {len(users)}")
    print(f"Already had preferences: {len(existing_user_ids)}")
    print(f"New preferences created: {len(result.inserted_ids)}")
    print("=" * 50)

    client.close()
    print("\nMigration complete!")


if __name__ == "__main__":
    print("User Preferences Migration Script")
    print("-" * 40)
    asyncio.run(migrate_preferences())
