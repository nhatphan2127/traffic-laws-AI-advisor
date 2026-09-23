# api/retrieval.py
import logging
from typing import List, Optional
import requests

from core.schema import RetrievalDocument
from core.load_settings import load_settings
from core.setup_logging import setup_logging

# --- Initialization ---
settings = load_settings()
setup_logging()
logger = logging.getLogger("api")

api_settings = settings.get("api", {})

BASE_API_URL = api_settings.get("base_url", "http://localhost:5555").rstrip("/")
RETRIEVAL_API_URL = api_settings.get("retrieval_api_url", f"{BASE_API_URL}/api/retrieval")
EXTRACT_API_URL = api_settings.get("extract_api_url", f"{BASE_API_URL}/api/extract-relevant-clause-point")
REQUEST_TIMEOUT = api_settings.get("request_timeout", 30)


def _parse_documents(raw_results: list) -> List[RetrievalDocument]:
    """Hàm phụ trợ parse list JSON response thành list[RetrievalDocument]."""
    documents: List[RetrievalDocument] = []
    for item in raw_results:
        doc = RetrievalDocument(
            id=str(item.get("id", "")),
            total_score=float(item.get("total_score", 0.0)),
            dense_score=float(item.get("dense_score", 0.0)),
            sparse_score=float(item.get("sparse_score", 0.0)),
            text=item.get("text", ""),
            metadata=item.get("metadata", {})
        )
        documents.append(doc)
    return documents


def retrievalApi(query: str, top_k: Optional[int] = None) -> List[RetrievalDocument]:
    """
    Gửi request HTTP đến Retrieval Service để thực hiện Hybrid Search + Reranking.
    Trả về danh sách các đối tượng RetrievalDocument.
    """
    clean_query = (query or "").strip()
    if not clean_query:
        logger.warning("retrievalApi: Empty query provided. Skipping retrieval.")
        return []

    payload = {"query": clean_query}
    if top_k is not None:
        payload["top_k"] = top_k

    try:
        logger.info(f"retrievalApi: Sending retrieval request to {RETRIEVAL_API_URL} for: '{clean_query}'")
        
        response = requests.post(
            RETRIEVAL_API_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code != 200:
            logger.error(
                f"retrievalApi: Request failed with status code {response.status_code}: {response.text}"
            )
            return []

        data = response.json()
        raw_results = data.get("results", [])
        documents = _parse_documents(raw_results)

        logger.info(f"retrievalApi: Successfully received {len(documents)} docs from API.")
        return documents

    except requests.exceptions.Timeout:
        logger.error(f"retrievalApi: Request timed out ({REQUEST_TIMEOUT}s) calling {RETRIEVAL_API_URL}")
        return []
    except requests.exceptions.ConnectionError:
        logger.error(f"retrievalApi: Failed to connect to retrieval service at {RETRIEVAL_API_URL}")
        return []
    except Exception as e:
        logger.error(f"retrievalApi: Unexpected error during retrieval API call: {e}", exc_info=True)
        return []


def extractRelevantClausePointApi(
    article: int,
    clause: Optional[int] = None,
    point: Optional[str] = None
) -> List[RetrievalDocument]:
    """
    Gửi request HTTP đến Retrieval Service để lọc các văn bản tham chiếu Điều/Khoản/Điểm.
    Trả về danh sách các đối tượng RetrievalDocument.
    """
    if article is None:
        logger.warning("extractRelevantClausePointApi: 'article' parameter is required. Skipping extraction.")
        return []

    payload = {
        "article": article,
        "clause": clause,
        "point": point
    }

    try:
        logger.info(
            f"extractRelevantClausePointApi: Sending extract request: Article={article}, Clause={clause}, Point={point}"
        )
        response = requests.post(
            EXTRACT_API_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code != 200:
            logger.error(
                f"extractRelevantClausePointApi: Request failed with status code {response.status_code}: {response.text}"
            )
            return []

        data = response.json()
        raw_results = data.get("results", [])
        documents = _parse_documents(raw_results)

        logger.info(f"extractRelevantClausePointApi: Successfully received {len(documents)} docs for Article {article}.")
        return documents

    except requests.exceptions.Timeout:
        logger.error(f"extractRelevantClausePointApi: Request timed out ({REQUEST_TIMEOUT}s) calling {EXTRACT_API_URL}")
        return []
    except requests.exceptions.ConnectionError:
        logger.error(f"extractRelevantClausePointApi: Failed to connect to extract service at {EXTRACT_API_URL}")
        return []
    except Exception as e:
        logger.error(f"extractRelevantClausePointApi: Unexpected error during extract API call: {e}", exc_info=True)
        return []