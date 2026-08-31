import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError
from core.load_settings import load_settings
from core.setup_logging import setup_logging

settings = load_settings()
setup_logging()
logger = logging.getLogger("backend")

try:
    MONGODB_URI = settings['backend']['mongodb_uri']
    DB_NAME = settings['backend']['db_name']

    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    
    client.admin.command('ping') 
    logger.info("Successfully connected to MongoDB")

    db = client[DB_NAME]
    users_collection = db["users"]
    chats_collection = db["chats"]

except KeyError as e:
    logger.critical(f"Missing configuration key: {e}")
    raise e 
except (ConnectionFailure, ConfigurationError) as e:
    logger.critical(f"Không thể kết nối tới MongoDB: {e}")
    raise e