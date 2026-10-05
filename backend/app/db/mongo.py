import logging
from functools import lru_cache

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ConfigurationError

from app.core.config import load_settings

logger = logging.getLogger("server")


@lru_cache
def get_database() -> Database:
    """Connect lazily (first use) instead of at import time."""
    backend = load_settings()['backend']
    try:
        client = MongoClient(backend['mongodb_uri'], serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        return client[backend['db_name']]
    except KeyError as e:
        logger.critical(f"Missing configuration key: {e}")
        raise
    except (ConnectionFailure, ConfigurationError) as e:
        logger.critical(f"Không thể kết nối tới MongoDB: {e}")
        raise


def users_collection() -> Collection:
    return get_database()["users"]


def chats_collection() -> Collection:
    return get_database()["chats"]
