import logging
from functools import lru_cache
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Prefetch, FusionQuery, Fusion
from sentence_transformers import CrossEncoder

from app.vectorstore.qdrant import get_qdrant_client, ensure_collection
from app.vectorstore.bm25 import BM25
from app.core.config import load_settings, BM25_PATH
from app.embedding.embed_texts import embed_texts
from app.core.schema import RetrievalDocument

# --- Initialization ---
settings = load_settings()
logger = logging.getLogger('retrieval')
retrieval_settings = settings['retrieval']

COLLECTION_NAME = settings['vector_database']['collection_name']
TOP_K = retrieval_settings['top_k']
RRF_K = retrieval_settings['rrf_k']
DENSE_THRESHOLD = retrieval_settings['dense_threshold']

RERANKER_CONFIG = retrieval_settings['reranker']
reranker_model = None
if RERANKER_CONFIG.get("enabled"):
    logger.info(f"Loading Reranker model: {RERANKER_CONFIG.get('model')}")
    reranker_model = CrossEncoder(RERANKER_CONFIG.get("model", "cross-encoder/ms-marco-MiniLM-L-6-v2"))


@lru_cache(maxsize=1)
def _load_bm25() -> Optional[BM25]:
    """Load the BM25 model once per process instead of on every query."""
    return BM25.load_model(BM25_PATH)


def get_hybrid_results(client: QdrantClient, query: str, query_embedding: list[float], limit: int) -> list[RetrievalDocument]:
    """Retrieves and ranks documents using Hybrid search (Dense + Sparse) with RRF fusion in Qdrant."""
    ensure_collection(client=client)
    
    # BM25 model generates the sparse vector for the query
    bm25 = _load_bm25()
    
    if not bm25:
        logger.error("BM25 model not found, falling back to dense only search.")
        response = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_embedding,
            using="dense",
            limit=limit,
            score_threshold=DENSE_THRESHOLD
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

def retrieval(query: str, top_k: Optional[int] = None) -> list[RetrievalDocument]:
    """Main orchestrator function for hybrid retrieval with RRF and Reranking."""
    top_k = top_k or TOP_K
    query_embeddings = embed_texts([query])
    if not query_embeddings or not query_embeddings[0]:
        logger.error('Error in processing query embedding')
        return []
    
    query_embedding = query_embeddings[0]
    client: QdrantClient = get_qdrant_client()

    # Step 1: Hybrid Search (Dense + Sparse) with RRF fusion
    candidate_limit = RERANKER_CONFIG.get("top_n", top_k) * 4 if RERANKER_CONFIG.get("enabled") else top_k
    
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
        top_n = RERANKER_CONFIG.get("top_n", top_k)
        final_results = rerank_results(query, hybrid_results, top_n)
    else:
        final_results = hybrid_results[:top_k]

    logger.info(f'Successfully retrieved {len(final_results)} items')
    return final_results
