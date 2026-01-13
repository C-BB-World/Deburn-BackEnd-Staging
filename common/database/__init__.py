"""
Database module - Generic async MongoDB connection using Beanie ODM.
"""

from common.database.mongodb import MongoDB
from common.database.base_document import BaseDocument

__all__ = ["MongoDB", "BaseDocument"]
