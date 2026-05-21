import logging
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from core.load_settings import load_settings

settings = load_settings()
logger = logging.getLogger('vector_datatbase')

_client = None
VECTOR_DB_SETTINGS = settings['vector_database']
# qdrant.py - course-chatbot/...

# VECTOR_DB SETTINGS
VECTOR_DB_TYPE = VECTOR_DB_SETTINGS.get("type", "qdrant")
VECTOR_DB_HOST = VECTOR_DB_SETTINGS.get("host", "localhost")
VECTOR_DB_PORT = VECTOR_DB_SETTINGS.get("port", 6333)
VECTOR_DB_URL = VECTOR_DB_SETTINGS.get("url", f"http://{VECTOR_DB_HOST}:{VECTOR_DB_PORT}")
VECTOR_DB_API_KEY = VECTOR_DB_SETTINGS.get("api_key", None)
VECTOR_DB_COLLECTION = VECTOR_DB_SETTINGS.get("collection_name", "default_collection")
VECTOR_DB_DISTANCE = VECTOR_DB_SETTINGS.get("distance", "cosine")
VECTOR_DB_SIZE = VECTOR_DB_SETTINGS.get("vector_size", "cosine")
VECTOR_DB_TIMEOUT = VECTOR_DB_SETTINGS.get("timeout", 30)


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is not None:
        return _client

    try:
        # ket noi qua url neu co
        if VECTOR_DB_URL:
            logger.info("Connecting to Qdrant via URL")
            _client = QdrantClient(
                url=VECTOR_DB_URL,
                api_key=VECTOR_DB_API_KEY,
                timeout=VECTOR_DB_TIMEOUT
            )
        else:
            logger.info(f"Connecting to Qdrant at {VECTOR_DB_HOST}:{VECTOR_DB_PORT}")
            _client = QdrantClient(
                host=VECTOR_DB_HOST,
                port=VECTOR_DB_PORT,
                api_key=VECTOR_DB_API_KEY,
                timeout=VECTOR_DB_TIMEOUT
            )

        # Test connection
        _client.get_collections()
        logger.info("Successfully connected to Qdrant")
        return _client

    except Exception as e:
        logger.error(f"Failed to connect to Qdrant: {e}")
        raise ConnectionError(f"Cannot connect to Qdrant database: {e}")
    

def ensure_collection(client: QdrantClient):
    existing_collections = [collection.name for collection in client.get_collections().collections]

    if VECTOR_DB_COLLECTION in existing_collections:
        logger.info(f"Collection '{VECTOR_DB_COLLECTION}' already exists.")
        return

    logger.info(f"Creating collection '{VECTOR_DB_COLLECTION}'...")
    client.recreate_collection(
        collection_name=VECTOR_DB_COLLECTION,
        vectors_config=VectorParams(
            size=VECTOR_DB_SIZE,
            distance=Distance[VECTOR_DB_DISTANCE.upper()]
        )
    )

    logger.info(f"Collection '{VECTOR_DB_COLLECTION}' created successfully.")