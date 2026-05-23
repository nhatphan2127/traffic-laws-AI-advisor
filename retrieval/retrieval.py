import logging
from dataclasses import dataclass
from typing import Any
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import ScoredPoint
from sentence_transformers import CrossEncoder

from vectorstore.qdrant import get_qdrant_client, ensure_collection
from vectorstore.bm25 import BM25
from core.load_settings import load_settings
from core.setup_logging import setup_logging
from embedding.embed_texts import embed_texts
from core.schema import RetrievalDocument

# --- 2. Initialization ---
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
    reranker_model = CrossEncoder(RERANKER_CONFIG.get("model_name", "cross-encoder/ms-marco-MiniLM-L-6-v2"))

# --- 3. Sub-functions ---

def get_dense_results(client: QdrantClient, query_embedding: list[float], limit: int) -> list[ScoredPoint]:
    """Retrieves and ranks documents using Dense vector search (Qdrant)."""
    ensure_collection(client=client)
    
    # Qdrant returns points already sorted by dense score descending
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        limit=limit,
        score_threshold=DENSE_SCORE_THRESHOLD
    )
    return results.points


def get_sparse_ranked_scores(query: str, points: list[ScoredPoint], bm25: BM25) -> list[tuple[str, float]]:
    """Scores documents using BM25 and returns them sorted by score descending."""
    sparse_scores = []
    
    for p in points:
        doc_id = str(p.id)
        text = p.payload.get('text', '')
        score = bm25.score(query=query, doc=text)
        sparse_scores.append((doc_id, score))
        
    # Sort descending to determine the BM25 rank
    sparse_scores.sort(key=lambda x: x[1], reverse=True)
    return sparse_scores


def rerank_results(query: str, documents: list[RetrievalDocument], top_n: int) -> list[RetrievalDocument]:
    """Reranks the retrieved documents using a Cross-Encoder."""
    if not reranker_model or not documents:
        return documents[:top_n]

    pairs = [[query, doc.text] for doc in documents]
    scores = reranker_model.predict(pairs)

    for i, doc in enumerate(documents):
        doc.total_score = float(scores[i])

    # Sort by cross-encoder score descending
    documents.sort(key=lambda x: x.total_score, reverse=True)
    return documents[:top_n]


def compute_rrf_and_combine(
    dense_points: list[ScoredPoint], 
    sparse_ranked: list[tuple[str, float]], 
    rrf_k: int = 60
) -> list[RetrievalDocument]:
    """Combines Dense and Sparse ranks using the Reciprocal Rank Fusion (RRF) formula."""
    
    # 1. Map documents to their Dense Rank and Score
    dense_rank_map = {str(p.id): rank + 1 for rank, p in enumerate(dense_points)}
    dense_score_map = {str(p.id): p.score for p in dense_points}
    payload_map = {str(p.id): p.payload for p in dense_points}

    # 2. Map documents to their Sparse (BM25) Rank and Score
    sparse_rank_map = {doc_id: rank + 1 for rank, (doc_id, _) in enumerate(sparse_ranked)}
    sparse_score_map = {doc_id: score for doc_id, score in sparse_ranked}

    retrieval_docs = []
    
    # 3. Calculate RRF score for each document
    for doc_id in dense_rank_map.keys():
        d_rank = dense_rank_map[doc_id]
        s_rank = sparse_rank_map[doc_id]
        
        # RRF Formula: 1 / (k + rank)
        rrf_score = (1.0 / (rrf_k + d_rank)) + (1.0 / (rrf_k + s_rank))
        
        payload = payload_map[doc_id]
        text = payload.pop('text', '')  # extract text, leave the rest as metadata
        
        doc = RetrievalDocument(
            id=doc_id,
            total_score=rrf_score,
            sparse_score=sparse_score_map[doc_id],
            dense_score=dense_score_map[doc_id],
            
            text=text,
            metadata=payload
        )
        retrieval_docs.append(doc)

    # 4. Sort the final documents by their combined RRF Total Score descending
    retrieval_docs.sort(key=lambda x: x.total_score, reverse=True)
    
    return retrieval_docs


# --- 4. Main Retrieval Function ---

def retrieval(query: str) -> list[RetrievalDocument]:
    """Main orchestrator function for hybrid retrieval with RRF."""
    query_embeddings = embed_texts([query])
    if not query_embeddings or not query_embeddings[0]:
        logger.error('Error in processing query embedding')
        return []
    
    query_embedding = query_embeddings[0]
    
    client: QdrantClient = get_qdrant_client()
    path = Path("./vectorstore/bm25store/bm25store.pkl")
    bm25: BM25 = BM25.load_model(path)

    # Step 1: Get top candidates using Dense Search (multiplying by 3 to get a larger candidate pool for re-ranking)
    candidate_limit = TOP_K * 3
    dense_points = get_dense_results(client, query_embedding, candidate_limit)
    
    if not dense_points:
        return []

    # Step 2: Score those exact candidates using Sparse Search (BM25)
    sparse_ranked = get_sparse_ranked_scores(query, dense_points, bm25)

    # Step 3: Compute RRF using both ranked lists
    rrf_results = compute_rrf_and_combine(dense_points, sparse_ranked, rrf_k=TOP_K * 3)

    # Step 4: Post-reranking
    if RERANKER_CONFIG.get("enabled"):
        top_n = RERANKER_CONFIG.get("top_n", TOP_K)
        final_results = rerank_results(query, rrf_results, top_n)
    else:
        final_results = rrf_results[:TOP_K]

    # Step 5: Return the final results
    logger.info(f'Success retrieval {len(final_results)} items')
    return final_results
