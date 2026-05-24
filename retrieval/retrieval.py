import logging
from typing import Any
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Prefetch, FusionQuery, Fusion
from sentence_transformers import CrossEncoder

from vectorstore.qdrant import get_qdrant_client, ensure_collection
from vectorstore.bm25 import BM25
from core.load_settings import load_settings
from core.setup_logging import setup_logging
from embedding.embed_texts import embed_texts
from core.schema import RetrievalDocument

# --- Initialization ---
settings = load_settings()
setup_logging()
logger = logging.getLogger('retrieval')

COLLECTION_NAME = settings['vector_database'].get("collection_name", "nmk_chatbot_collection")
TOP_K = settings['retrieval'].get("top_k", 5)
RRF_K = settings['retrieval'].get("rrf_k", 60)
DENSE_SCORE_THRESHOLD = settings['retrieval'].get('dense_score_threshold', 0.4)

RERANKER_CONFIG = settings['retrieval'].get("reranker", {"enabled": False})
reranker_model = None
if RERANKER_CONFIG.get("enabled"):
    logger.info(f"Loading Reranker model: {RERANKER_CONFIG.get('model_name')}")
    reranker_model = CrossEncoder(RERANKER_CONFIG.get("model_name", "cross-encoder/ms-marco-MiniLM-L-6-v2"))

# --- Sub-functions ---

def get_hybrid_results(client: QdrantClient, query: str, query_embedding: list[float], limit: int) -> list[RetrievalDocument]:
    """Retrieves and ranks documents using Hybrid search (Dense + Sparse) with RRF fusion in Qdrant."""
    ensure_collection(client=client)
    
    # Load BM25 model to generate sparse vector for query
    bm25_path = Path("./vectorstore/bm25store/bm25store.pkl")
    bm25 = BM25.load_model(bm25_path)
    
    if not bm25:
        logger.error("BM25 model not found, falling back to dense only search.")
        response = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_embedding,
            using="dense",
            limit=limit,
            score_threshold=DENSE_SCORE_THRESHOLD
        )
        return [
            RetrievalDocument(
                id=str(p.id),
                total_score=p.score,
                dense_score=p.score,
                sparse_score=0.0,
                text=p.payload.get('text', ''),
                metadata={k: v for k, v in p.payload.items() if k != 'text'}
            ) for p in response.points
        ]

    sparse_vector = bm25.get_sparse_vector(query)

    # Perform hybrid search using Qdrant's Query API with RRF
    # Qdrant 1.10+ supports RRF fusion directly
    response = client.query_points(
        collection_name=COLLECTION_NAME,
        prefetch=[
            Prefetch(
                query=query_embedding,
                using="dense",
                limit=limit * 2,
            ),
            Prefetch(
                query=sparse_vector,
                using="sparse",
                limit=limit * 2,
            ),
        ],
        query=FusionQuery(fusion=Fusion.RRF), 
        limit=limit,
    )
    
    retrieval_docs = []
    for p in response.points:
        doc = RetrievalDocument(
            id=str(p.id),
            total_score=p.score,
            dense_score=0.0, 
            sparse_score=0.0,
            text=p.payload.get('text', ''),
            metadata={k: v for k, v in p.payload.items() if k != 'text'}
        )
        retrieval_docs.append(doc)
        
    return retrieval_docs


def rerank_results(query: str, documents: list[RetrievalDocument], top_n: int) -> list[RetrievalDocument]:
    """Reranks the retrieved documents using a Cross-Encoder."""
    if not reranker_model or not documents:
        return documents[:top_n]

    logger.info(f"Reranking {len(documents)} documents using Cross-Encoder...")
    pairs = [[query, doc.text] for doc in documents]
    scores = reranker_model.predict(pairs)

    for i, doc in enumerate(documents):
        doc.total_score = float(scores[i])

    # Sort by cross-encoder score descending
    documents.sort(key=lambda x: x.total_score, reverse=True)
    return documents[:top_n]


# --- Main Retrieval Function ---

def retrieval(query: str) -> list[RetrievalDocument]:
    """Main orchestrator function for hybrid retrieval with RRF and Reranking."""
    query_embeddings = embed_texts([query])
    if not query_embeddings or not query_embeddings[0]:
        logger.error('Error in processing query embedding')
        return []
    
    query_embedding = query_embeddings[0]
    client: QdrantClient = get_qdrant_client()

    # Step 1: Hybrid Search (Dense + Sparse) with RRF fusion
    candidate_limit = RERANKER_CONFIG.get("top_n", TOP_K) * 4 if RERANKER_CONFIG.get("enabled") else TOP_K
    
    hybrid_results = get_hybrid_results(
        client=client, 
        query=query, 
        query_embedding=query_embedding, 
        limit=candidate_limit
    )
    
    if not hybrid_results:
        logger.warning(f"No results found for query: {query}")
        return []

    # Step 2: Post-reranking
    if RERANKER_CONFIG.get("enabled"):
        top_n = RERANKER_CONFIG.get("top_n", TOP_K)
        final_results = rerank_results(query, hybrid_results, top_n)
    else:
        final_results = hybrid_results[:TOP_K]

    logger.info(f'Successfully retrieved {len(final_results)} items')
    return final_results
