"""MCP client for the retrieval service (retrieval_service, `/mcp` endpoint).

Usage (one MCP session per chat turn):

    async with RetrievalMCPClient().session() as retrieval:
        docs = await retrieval.search("...")
        refs = await retrieval.find_referencing_many([(6, 2, "a"), (7, None, None)])
"""
import asyncio
import contextlib
import json
import logging
from typing import Any, AsyncIterator, Iterable, Optional

from mcp import Client

from app.core.config import load_settings
from app.core.schema import RetrievalDocument

logger = logging.getLogger("clients")

SEARCH_TOOL = "search_legal_documents"
REFERENCES_TOOL = "find_referencing_chunks"

Reference = tuple[int, Optional[int], Optional[str]]


def _parse_documents(raw_results: list) -> list[RetrievalDocument]:
    return [
        RetrievalDocument(
            id=str(item.get("id", "")),
            total_score=float(item.get("total_score") or 0.0),
            dense_score=float(item.get("dense_score") or 0.0),
            sparse_score=float(item.get("sparse_score") or 0.0),
            text=item.get("text", ""),
            metadata=item.get("metadata") or {},
        )
        for item in raw_results
    ]


def _payload(result) -> dict:
    """Tool output: `structured_content`, or the JSON text block for servers that only send text."""
    if result.structured_content:
        return result.structured_content
    for block in result.content:
        text = getattr(block, "text", None)
        if not text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return {}


class RetrievalSession:
    """Typed wrapper around the retrieval tools of a connected MCP client."""

    def __init__(self, client: Client):
        self._client = client

    async def _call(self, tool: str, arguments: dict) -> list[RetrievalDocument]:
        try:
            result = await self._client.call_tool(tool, arguments)
        except Exception as e:
            logger.error(f"MCP call '{tool}' failed: {e}", exc_info=True)
            return []

        if result.is_error:
            message = " ".join(getattr(c, "text", "") for c in result.content)
            logger.error(f"MCP tool '{tool}' returned an error: {message}")
            return []

        documents = _parse_documents(_payload(result).get("results", []))
        logger.info(f"MCP tool '{tool}' returned {len(documents)} docs.")
        return documents

    async def search(self, query: str, top_k: Optional[int] = None) -> list[RetrievalDocument]:
        clean_query = (query or "").strip()
        if not clean_query:
            logger.warning("search: Empty query provided. Skipping retrieval.")
            return []
        arguments = {"query": clean_query}
        if top_k is not None:
            arguments["top_k"] = top_k
        return await self._call(SEARCH_TOOL, arguments)

    async def find_referencing(
        self, article: int, clause: Optional[int] = None, point: Optional[str] = None
    ) -> list[RetrievalDocument]:
        arguments = {"article": article}
        if clause is not None:
            arguments["clause"] = clause
        if point is not None:
            arguments["point"] = point
        return await self._call(REFERENCES_TOOL, arguments)

    async def find_referencing_many(self, refs: Iterable[Reference]) -> list[RetrievalDocument]:
        """Run reference lookups concurrently; returns docs de-duplicated by id, in order."""
        unique_refs = list(dict.fromkeys(refs))
        batches = await asyncio.gather(*(self.find_referencing(*ref) for ref in unique_refs))

        seen: set[str] = set()
        documents: list[RetrievalDocument] = []
        for doc in (d for batch in batches for d in batch):
            if doc.id not in seen:
                seen.add(doc.id)
                documents.append(doc)
        return documents


class RetrievalMCPClient:
    def __init__(self, url: Optional[Any] = None, timeout: Optional[float] = None):
        """`url` is the Streamable HTTP endpoint; tests may pass an in-process MCP server instead."""
        mcp_settings = load_settings()["mcp"]
        self.url = url or mcp_settings["retrieval_server_url"]
        self.timeout = timeout or mcp_settings["request_timeout"]

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[RetrievalSession]:
        """Open an MCP session; raises if the retrieval service is unreachable."""
        logger.debug(f"Opening MCP session to {self.url}")
        async with Client(self.url, read_timeout_seconds=self.timeout) as client:
            yield RetrievalSession(client)
