"""MCP server exposing the legal-document retrieval capabilities as tools.

The tools wrap `app.retrieval.hybrid` and `app.retrieval.references`. The server is mounted into the FastAPI app at
`/mcp` (Streamable HTTP) and can also run standalone over stdio
(`python -m app.mcp_server`).
"""
import logging
from typing import Annotated, Optional

from pydantic import BaseModel, Field
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

from app.core.config import load_settings
from app.core.schema import RetrievedChunk
from app.retrieval import hybrid, references

logger = logging.getLogger("mcp")

SERVER_INSTRUCTIONS = (
    "Tra cứu văn bản pháp luật giao thông đường bộ Việt Nam (Luật, Nghị định, Thông tư 2024). "
    "Dùng `search_legal_documents` để tìm các Điều/Khoản/Điểm liên quan tới một câu hỏi; "
    "câu truy vấn nên dùng thuật ngữ pháp lý (vd: 'xe mô tô, xe gắn máy' thay vì 'xe máy'). "
    "Dùng `find_referencing_chunks` để lấy các quy định viện dẫn tới một Điều/Khoản/Điểm cụ thể "
    "(vd: hình thức xử phạt bổ sung, biện pháp khắc phục hậu quả)."
)

_READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)


class SearchResult(BaseModel):
    query: str
    total_results: int
    results: list[RetrievedChunk]


class ReferenceResult(BaseModel):
    article: int
    clause: Optional[int] = None
    point: Optional[str] = None
    total_results: int
    results: list[RetrievedChunk]


mcp = MCPServer(
    name="legal-retrieval",
    title="Vietnamese Traffic Law Retrieval",
    instructions=SERVER_INSTRUCTIONS,
    version="1.0.0",
)


@mcp.tool(annotations=_READ_ONLY)
def search_legal_documents(
    query: Annotated[str, Field(min_length=1, description="Câu truy vấn pháp lý cần tìm.")],
    top_k: Annotated[
        Optional[int], Field(ge=1, le=50, description="Số kết quả trả về (mặc định theo cấu hình).")
    ] = None,
) -> SearchResult:
    """Hybrid search (dense + BM25 sparse, RRF fusion, optional reranking) over the legal corpus."""
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("query must not be empty")

    logger.info(f"[MCP] search_legal_documents query='{clean_query}' top_k={top_k}")
    docs = hybrid.retrieval(clean_query, top_k=top_k)
    chunks = [RetrievedChunk.from_document(doc) for doc in docs]
    return SearchResult(query=clean_query, total_results=len(chunks), results=chunks)


@mcp.tool(annotations=_READ_ONLY)
def find_referencing_chunks(
    article: Annotated[int, Field(ge=1, description="Số Điều được viện dẫn.")],
    clause: Annotated[Optional[int], Field(ge=1, description="Số Khoản được viện dẫn.")] = None,
    point: Annotated[Optional[str], Field(description="Ký hiệu Điểm được viện dẫn (vd: 'a').")] = None,
) -> ReferenceResult:
    """Return chunks whose `references` cite the given Article / Clause / Point."""
    logger.info(f"[MCP] find_referencing_chunks article={article} clause={clause} point={point}")
    docs = references.extract_relevant_clause_point(article=article, clause=clause, point=point)
    chunks = [RetrievedChunk.from_document(doc) for doc in docs]
    return ReferenceResult(
        article=article, clause=clause, point=point, total_results=len(chunks), results=chunks
    )


def transport_security() -> TransportSecuritySettings:
    """DNS-rebinding protection with hosts/origins configurable via MCP_ALLOWED_HOSTS / MCP_ALLOWED_ORIGINS."""
    mcp_settings = load_settings().get("mcp", {})
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=mcp_settings.get("allowed_hosts", ["127.0.0.1:*", "localhost:*"]),
        allowed_origins=mcp_settings.get("allowed_origins", ["http://127.0.0.1:*", "http://localhost:*"]),
    )


def streamable_http_app():
    """Starlette app serving the MCP endpoint at /mcp (stateless, JSON responses)."""
    return mcp.streamable_http_app(
        stateless_http=True,
        json_response=True,
        transport_security=transport_security(),
    )
