import logging
from typing import List, Dict, Any, Optional
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Project-specific imports
from retrieval.retrieval import retrieval
from utils.qdrant_filter import extract_relevant_clause_point
from core.schema import RetrievalDocument

logger = logging.getLogger("retrieval_api")

app = FastAPI(
    title="Hybrid Retrieval & Legal Clause Filter Service",
    description="API for Hybrid Search with RRF + Reranking and Qdrant Clause/Point Filtering.",
    version="1.0.0",
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request & Response Schemas ---
class RetrievalRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The search query text.")

class ExtractClauseRequest(BaseModel):
    article: int = Field(..., description="Target article number (Điều)")
    clause: Optional[int] = Field(None, description="Clause number (Khoản)")
    point: Optional[str] = Field(None, description="Point letter/number (Điểm)")

class RetrievalDocumentResponse(BaseModel):
    id: str
    total_score: float = 0.0
    dense_score: Optional[float] = 0.0
    sparse_score: Optional[float] = 0.0
    text: str
    metadata: Dict[str, Any] = {}

class RetrievalResponse(BaseModel):
    query: str
    total_results: int
    results: List[RetrievalDocumentResponse]

class ExtractClauseResponse(BaseModel):
    article: int
    clause: Optional[int] = None
    point: Optional[str] = None
    total_results: int
    results: List[RetrievalDocumentResponse]


# --- Helper Function ---
def serialize_doc(doc: RetrievalDocument) -> RetrievalDocumentResponse:
    """Converts a RetrievalDocument (dataclass or pydantic) into API response model."""
    if hasattr(doc, "__dataclass_fields__"):
        data = asdict(doc)
    elif hasattr(doc, "model_dump"):  # Pydantic v2
        data = doc.model_dump()
    elif hasattr(doc, "dict"):        # Pydantic v1
        data = doc.dict()
    else:
        data = {
            "id": getattr(doc, "id", ""),
            "total_score": getattr(doc, "total_score", 0.0),
            "dense_score": getattr(doc, "dense_score", 0.0),
            "sparse_score": getattr(doc, "sparse_score", 0.0),
            "text": getattr(doc, "text", ""),
            "metadata": getattr(doc, "metadata", {}),
        }

    return RetrievalDocumentResponse(**data)


# --- Health Check ---
@app.get("/api/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "ok"}


# --- Retrieval Endpoints ---
@app.post(
    "/api/retrieval", 
    response_model=RetrievalResponse, 
    status_code=status.HTTP_200_OK
)
def run_retrieval(req: RetrievalRequest):
    """
    POST: Hybrid Search with Dense + Sparse vectors, RRF fusion, and Cross-Encoder reranking.
    """
    clean_query = req.query.strip()
    if not clean_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Query string cannot be empty or whitespace only."
        )

    logger.info(f"Received retrieval request for query: '{clean_query}'")

    try:
        raw_docs = retrieval(clean_query)
        serialized_docs = [serialize_doc(doc) for doc in raw_docs]

        logger.info(f"Retrieved {len(serialized_docs)} documents for query: '{clean_query}'")
        return RetrievalResponse(
            query=clean_query,
            total_results=len(serialized_docs),
            results=serialized_docs,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during retrieval for query '{clean_query}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the retrieval request."
        )


@app.get(
    "/api/retrieval", 
    response_model=RetrievalResponse, 
    status_code=status.HTTP_200_OK
)
def run_retrieval_get(query: str = Query(..., min_length=1, description="Search query string")):
    """
    GET: Convenient for browser debugging and quick testing.
    """
    return run_retrieval(RetrievalRequest(query=query))


# --- Extract Relevant Clause/Point Endpoints ---
@app.post(
    "/api/extract-relevant-clause-point",
    response_model=ExtractClauseResponse,
    status_code=status.HTTP_200_OK
)
def run_extract_clause_point(req: ExtractClauseRequest):
    """
    POST: Finds all documents referencing a given Article, Clause, and Point.
    """
    logger.info(f"Received extract request: Article={req.article}, Clause={req.clause}, Point={req.point}")
    try:
        raw_docs = extract_relevant_clause_point(
            article=req.article,
            clause=req.clause,
            point=req.point
        )
        serialized_docs = [serialize_doc(doc) for doc in raw_docs]

        return ExtractClauseResponse(
            article=req.article,
            clause=req.clause,
            point=req.point,
            total_results=len(serialized_docs),
            results=serialized_docs
        )
    except Exception as e:
        logger.error(
            f"Error extracting clause/point (Article: {req.article}, Clause: {req.clause}, Point: {req.point}): {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract relevant clause/point from vector store."
        )


@app.get(
    "/api/extract-relevant-clause-point",
    response_model=ExtractClauseResponse,
    status_code=status.HTTP_200_OK
)
def run_extract_clause_point_get(
    article: int = Query(..., description="Target Article number (e.g. 5)"),
    clause: Optional[int] = Query(None, description="Target Clause number (e.g. 1)"),
    point: Optional[str] = Query(None, description="Target Point (e.g. 'a' or 'b')")
):
    """
    GET: Query parameters endpoint for extracting relevant clause/point.
    Example: /api/extract-relevant-clause-point?article=5&clause=1&point=a
    """
    req = ExtractClauseRequest(article=article, clause=clause, point=point)
    return run_extract_clause_point(req)


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Retrieval FastAPI application on port 5555...")
    uvicorn.run(app, host="0.0.0.0", port=5555)