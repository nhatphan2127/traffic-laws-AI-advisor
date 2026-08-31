import logging
from core.load_settings import load_settings
from core.setup_logging import setup_logging
from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
    Nested,
    NestedCondition,
    Record,
)
from vectorstore.qdrant import ensure_collection, get_qdrant_client
from core.schema import RetrievalDocument

setup_logging()
logger = logging.getLogger("tools")
settings = load_settings()

VECTOR_DB_SETTINGS = settings["vector_database"]
VECTOR_DB_COLLECTION = VECTOR_DB_SETTINGS.get(
    "collection_name", "default_collection"
)


def extract_relevant_clause_point(
    article: int,
    clause: int = None,
    point: str = None
) -> list[RetrievalDocument]:
    """Find all documents referencing the target article/clause/point."""

    _client: QdrantClient = get_qdrant_client()
    ensure_collection(_client)

    if article is None:
        logger.error("Cannot extract, article parameter is missing.")
        return []

    nested_conditions = [
        FieldCondition(
            key="article",
            match=MatchValue(value=article)
        )
    ]

    if clause is not None:
        nested_conditions.append(
            FieldCondition(
                key="clause",
                match=MatchValue(value=clause)
            )
        )

    if point is not None:
        nested_conditions.append(
            FieldCondition(
                key="point",
                match=MatchValue(value=point)
            )
        )

    scroll_filter = Filter(
        must=[
            NestedCondition(
                nested=Nested(
                    key="references",
                    filter=Filter(must=nested_conditions)
                )
            )
        ]
    )

    results, _ = _client.scroll(
        collection_name=VECTOR_DB_COLLECTION,
        scroll_filter=scroll_filter,
        limit=50,
    )

    logger.info(
        f"Function 1 - Filtered {len(results)} items "
        f"referencing Article {article}, "
        f"Clause {clause}, Point {point}"
    )

    # Convert Qdrant Record -> RetrievalDocument
    retrieval_docs = []

    for p in results:
        doc = RetrievalDocument(
            id=str(p.id),
            total_score=0.0,
            dense_score=0.0,
            sparse_score=0.0,
            text=p.payload.get("text", ""),
            metadata={
                k: v
                for k, v in p.payload.items()
                if k != "text"
            }
        )

        retrieval_docs.append(doc)

    return retrieval_docs
