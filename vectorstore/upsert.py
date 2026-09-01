import logging
from qdrant_client import QdrantClient

from core.load_settings import load_settings
from vectorstore.qdrant import get_qdrant_client, ensure_collection
from vectorstore.index import build_qdrant_points

settings = load_settings()
logger = logging.getLogger("vectorstore")

QDRANT_CONFIG = settings["vector_database"]
COLLECTION_NAME = QDRANT_CONFIG["collection_name"]

def upsert_chunks(chunks: list[dict]):
    BATCH_SIZE = 100
    
    if not chunks:
        logger.warning("No chunks provided to build Qdrant points.")
        return []
    
    client: QdrantClient = get_qdrant_client()
    ensure_collection(client)
    points = build_qdrant_points(chunks)
    
    if not points:
        logger.warning("No points were built from the provided chunks.")
        return []
    
    total_points = len(points)
    logger.info(f"Starting upsert for {total_points} points in batches of {BATCH_SIZE}...")
    
    for i in range(0, total_points, BATCH_SIZE):
        batch = points[i : i + BATCH_SIZE]
        client.upsert(
            collection_name=COLLECTION_NAME, 
            points=batch
        )
        logger.info(f"Upserted batch {i // BATCH_SIZE + 1}/{(total_points + BATCH_SIZE - 1) // BATCH_SIZE} ({len(batch)} points)")
        
    logger.info(f" Successfully upserted all {total_points} points into collection '{COLLECTION_NAME}'.")
    return points