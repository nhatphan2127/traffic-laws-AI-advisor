import asyncio
import logging
from dataclasses import asdict
from typing import AsyncIterator, Dict, List, Optional, Tuple

from app.clients.retrieval_mcp import Reference, RetrievalMCPClient
from app.core.schema import RetrievalDocument
from app.guardrails.input.rule_based import check_input_rules
from app.guardrails.input.semantic import check_input_semantics
from app.llm.model import LLMModel
from app.llm.prompts import get_rag_prompt, SYSTEM_PROMPT, LEGAL_QUERY_NORMALIZATION_PROMPT

logger = logging.getLogger("llm")

MAX_HISTORY_TURNS = 8

# (debug docs, answer, thinking)
ChatChunk = Tuple[List[dict], str, str]


def _reference_of(doc: RetrievalDocument) -> Optional[Reference]:
    """Article/Clause/Point of a retrieved chunk, used to look up chunks that cite it."""
    metadata = doc.metadata or {}
    try:
        article_raw = metadata.get('article_number')
        clause_raw = metadata.get('clause_number')
        article = int(article_raw) if article_raw is not None else None
        clause = int(clause_raw) if clause_raw is not None else None
    except (ValueError, TypeError) as e:
        logger.warning(f"Metadata extraction warning for document {doc.id}: {e}")
        return None

    point = metadata.get('point') if metadata.get('is_point') else None
    if not article:
        return None
    return article, clause, point


class ChatEngine:
    def __init__(self, llm: Optional[LLMModel] = None, retrieval: Optional[RetrievalMCPClient] = None):
        try:
            self.llm = llm or LLMModel()
            logger.info("LLMModel initialized successfully in ChatEngine.")
        except Exception as e:
            logger.critical(f"Failed to initialize LLMModel in ChatEngine: {e}", exc_info=True)
            raise
        self.retrieval = retrieval or RetrievalMCPClient()
        logger.info(f"Retrieval MCP server: {self.retrieval.url}")

    def normalize_query(self, query: str) -> str:
        """
        Normalizes a user query into a legal query containing appropriate legal terminology.
        """
        try:
            prompt_content = LEGAL_QUERY_NORMALIZATION_PROMPT.format(USER_QUERY=query)
            messages = [{"role": "user", "content": prompt_content}]

            normalized = self.llm.generate(messages, stream=False)

            if isinstance(normalized, tuple):
                thinking, content = normalized
                normalized = content if content else thinking

            normalized = str(normalized or "").strip()
            logger.debug(f"[QUERY NORMALIZATION] Raw LLM output: '{normalized}'")

            # Strip any quotes if LLM wraps the query in them
            if normalized.startswith('"') and normalized.endswith('"'):
                normalized = normalized[1:-1].strip()
            if normalized.startswith("'") and normalized.endswith("'"):
                normalized = normalized[1:-1].strip()

            if not normalized:
                logger.warning("[QUERY NORMALIZATION] LLM returned empty string. Falling back to original query.")
                return query

            return normalized
        except Exception as e:
            logger.error(f"Error during query normalization: {e}", exc_info=True)
            return query

    async def retrieve(self, query: str) -> Tuple[List[RetrievalDocument], List[RetrievalDocument]]:
        """Hybrid search + reference expansion over one MCP session.

        Returns (primary docs, referencing docs not already in the primary set).
        """
        docs: List[RetrievalDocument] = []
        relevant_docs: List[RetrievalDocument] = []
        try:
            async with self.retrieval.session() as session:
                docs = await session.search(query)
                logger.info(f"Retrieved {len(docs)} primary documents from database.")

                refs = [ref for ref in map(_reference_of, docs) if ref]
                primary_ids = {doc.id for doc in docs}
                relevant_docs = [
                    doc for doc in await session.find_referencing_many(refs) if doc.id not in primary_ids
                ]
        except Exception as e:
            logger.error(f"Error during document retrieval via MCP: {e}", exc_info=True)
        return docs, relevant_docs

    async def chat(self, query: str, history: Optional[List[Dict[str, str]]] = None) -> AsyncIterator[ChatChunk]:
        """
        Executes guardrails, RAG retrieval and LLM generation.
        Yields tuples: (debug_json_list, answer, thinking)
        """
        history = history or []

        # 0. Input guardrails: cheap rule checks first, then the LLM semantic check.
        rule_result = check_input_rules(query=query, history=history)
        if rule_result.action == "block":
            logger.warning(f"Input blocked by rule guardrail: {rule_result.reason}")
            yield [], rule_result.message, ""
            return

        semantic_result = await asyncio.to_thread(check_input_semantics, query, history, self.llm)
        if semantic_result.action != "allow":
            logger.warning(f"Input blocked by semantic guardrail: {semantic_result.reason}")
            yield [], semantic_result.message, ""
            return

        logger.info(f"Executing chat engine for query: '{query}'")

        # 1. Query Normalization
        normalized_query = await asyncio.to_thread(self.normalize_query, query)
        logger.info(f"[QUERY NORMALIZATION] Normalized query: {normalized_query}")

        # 2-3. Retrieval + reference expansion (MCP)
        docs, relevant_docs = await self.retrieve(normalized_query)

        # 4. Prepare Debug Metadata & Prompt
        all_docs = docs + relevant_docs
        logger.info(f"Total contextual document references: {len(all_docs)}")
        debug_json_list = [asdict(doc) for doc in all_docs]

        try:
            rag_prompt = get_rag_prompt(query, all_docs)
        except Exception as e:
            logger.error(f"Error generating RAG prompt: {e}", exc_info=True)
            rag_prompt = query

        # 5. Build Chat Messages History
        formatted_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        formatted_messages.extend(history[-MAX_HISTORY_TURNS:])
        formatted_messages.append({"role": "user", "content": rag_prompt})

        # 6. Generate, validate, then expose the complete answer.
        try:
            logger.info("Starting response generation from LLM...")
            response = await asyncio.to_thread(self.llm.generate, formatted_messages, False)
            if isinstance(response, tuple):
                answer = response[1] if len(response) > 1 else response[0]
            else:
                answer = response
            answer = str(answer or "").strip()

            yield debug_json_list, answer, ""
        except Exception as e:
            logger.error(f"Error during LLM response generation: {e}", exc_info=True)
            yield debug_json_list, "An error occurred while generating the response.", ""
