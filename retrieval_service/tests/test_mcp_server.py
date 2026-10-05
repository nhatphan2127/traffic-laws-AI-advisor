"""MCP server tests with stubbed retrieval (no Qdrant / embedding model needed).

Run from the retrieval_service folder:  python -m pytest
"""

import pytest

from mcp import Client

from app.core.schema import RetrievalDocument
from app.mcp_server import server

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _doc(i: int, article: int = 6) -> RetrievalDocument:
    return RetrievalDocument(
        id=str(i), total_score=1.0 / (i + 1), sparse_score=0.0, dense_score=0.0,
        text=f"chunk {i}", metadata={"article_number": article, "clause_number": 1, "point": "a"},
    )


@pytest.fixture(autouse=True)
def stub_retrieval(monkeypatch):
    calls = {}

    def fake_retrieval(query, top_k=None):
        calls["search"] = (query, top_k)
        return [_doc(i) for i in range(top_k or 3)]

    def fake_refs(article, clause=None, point=None):
        calls["refs"] = (article, clause, point)
        return [_doc(10, article=article)]

    monkeypatch.setattr(server.hybrid, "retrieval", fake_retrieval)
    monkeypatch.setattr(server.references, "extract_relevant_clause_point", fake_refs)
    return calls


async def test_lists_tools_with_schemas():
    async with Client(server.mcp) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
    assert set(tools) == {"search_legal_documents", "find_referencing_chunks"}
    assert tools["search_legal_documents"].input_schema["required"] == ["query"]
    assert tools["search_legal_documents"].output_schema is not None
    assert tools["find_referencing_chunks"].annotations.read_only_hint is True


async def test_search_returns_structured_chunks(stub_retrieval):
    async with Client(server.mcp) as client:
        result = await client.call_tool("search_legal_documents", {"query": "  vượt đèn đỏ ", "top_k": 2})
    assert not result.is_error
    assert stub_retrieval["search"] == ("vượt đèn đỏ", 2)
    assert result.structured_content["total_results"] == 2
    assert result.structured_content["results"][0]["metadata"]["article_number"] == 6


async def test_find_referencing_chunks(stub_retrieval):
    async with Client(server.mcp) as client:
        result = await client.call_tool("find_referencing_chunks", {"article": 6, "clause": 2, "point": "a"})
    assert not result.is_error
    assert stub_retrieval["refs"] == (6, 2, "a")
    assert result.structured_content["article"] == 6
    assert result.structured_content["total_results"] == 1


async def test_invalid_arguments_are_tool_errors():
    async with Client(server.mcp) as client:
        result = await client.call_tool("find_referencing_chunks", {"article": 0})
    assert result.is_error
