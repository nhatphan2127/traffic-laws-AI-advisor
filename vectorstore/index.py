import logging
import uuid
from pathlib import Path

from embedding.embed_texts import embed_texts
from core.load_settings import load_settings
from vectorstore.bm25 import BM25


logger = logging.getLogger("embedding")
settings = load_settings()


def build_qdrant_points(chunks: list[dict]) -> list[dict]:
    if not chunks:
        logger.warning("No chunks provided to build Qdrant points.")
        return []
    
    # Extract texts for embedding and sparse vector generation
    texts = [chunk["text"] for chunk in chunks]
    
    # Generate dense embeddings
    embeddings = embed_texts(texts)
    if not embeddings:
        logger.warning("No embeddings generated for the provided texts.")
        return []
    
    # Load BM25 for sparse vector generation
    bm25_path = Path("./vectorstore/bm25store/bm25store.pkl")
    bm25 = BM25.load_model(bm25_path)
    if not bm25:
        logger.warning("BM25 model not found, sparse vectors will not be generated.")
    
    points = []
    
    for chunk, dense_vector in zip(chunks, embeddings):
        point_vector = {
            "dense": dense_vector
        }
        
        if bm25:
            sparse_vector = bm25.get_sparse_vector(chunk["text"])
            point_vector["sparse"] = sparse_vector
            
        points.append({
            "id": str(uuid.uuid4()),
            "vector": point_vector,
            "payload": {
                "text": chunk["text"],
                **chunk.get("metadata", {})
            }
        })
        
    logger.info(f"Built {len(points)} Qdrant points with hybrid vectors.")
    return points
