import logging
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, SparseVectorParams

from core.load_settings import load_settings

settings = load_settings()
logger = logging.getLogger('vectorstore')

_client = None
vector_db_settings = settings['vector_database']

# VECTOR_DB SETTINGS
VECTOR_DB_TYPE = vector_db_settings['type']
VECTOR_DB_HOST = vector_db_settings['host']
VECTOR_DB_PORT = vector_db_settings['port']
VECTOR_DB_URL = vector_db_settings['url']
VECTOR_DB_API_KEY = vector_db_settings['api_key']
VECTOR_DB_COLLECTION = vector_db_settings['collection_name']
VECTOR_DB_DISTANCE = vector_db_settings['distance']
VECTOR_DB_SIZE = vector_db_settings['vector_size']
VECTOR_DB_TIMEOUT = vector_db_settings['timeout']


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is not None:
        return _client

    try:
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

    logger.info(f"Creating collection '{VECTOR_DB_COLLECTION}' with hybrid support...")
    client.recreate_collection(
        collection_name=VECTOR_DB_COLLECTION,
        vectors_config={
            "dense": VectorParams(
                size=VECTOR_DB_SIZE,
                distance=Distance[VECTOR_DB_DISTANCE.upper()]
            )
        },
        sparse_vectors_config={
            "sparse": SparseVectorParams()
        }
    )

    logger.info(f"Collection '{VECTOR_DB_COLLECTION}' created successfully.")
