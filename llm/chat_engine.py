import json
import logging
from typing import List, Dict, Generator, Optional
from dataclasses import asdict

from retrieval.retrieval import retrieval
from llm.model import LLMModel
from llm.promt_template import get_rag_prompt, SYSTEM_PROMPT, LEGAL_QUERY_NORMALIZATION_PROMPT
from tools.qdrant_filter import extract_relevant_clause_point

logger = logging.getLogger("chat_engine")

class ChatEngine:
    def __init__(self):
        try:
            self.llm = LLMModel()
            logger.info("LLMModel initialized successfully in ChatEngine.")
        except Exception as e:
            logger.critical(f"Failed to initialize LLMModel in ChatEngine: {e}", exc_info=True)
            raise e

    def normalize_query(self, query: str) -> str:
        """
        Normalizes a user query into a legal query containing appropriate legal terminology.
        """
        try:
            prompt_content = LEGAL_QUERY_NORMALIZATION_PROMPT.format(USER_QUERY=query)
            messages = [{"role": "user", "content": prompt_content}]
            
            # Use generate_with_tools without tools to get a single generation
            _, normalized = self.llm.generate_with_tools(
                messages, tools=None, provider="cloud_ollama", stream=False
            )
            normalized = normalized.strip()
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

    def chat(self, query: str, history: Optional[List[Dict[str, str]]] = None) -> Generator:
        """
        Executes RAG retrieval and streams LLM response chunks.
        Yields tuples: (debug_json_list, answer, thinking)
        """
        if history is None:
            history = []

        logger.info(f"Executing chat engine for query: '{query}'")
        logger.info(f"[QUERY NORMALIZATION] Original query: {query}")
        
        # 1. Query Normalization
        normalized_query = self.normalize_query(query)
        logger.info(f"[QUERY NORMALIZATION] Normalized query: {normalized_query}")

        # 2. RAG Retrieval with Exception Handling
        docs = []
        try:
            docs = retrieval(normalized_query)
            logger.info(f"Retrieved {len(docs)} primary documents from database.")
        except Exception as e:
            logger.error(f"Error during document retrieval: {e}", exc_info=True)

        # 3. Extract Relevant Clauses and Points
        relevant_docs = []
        for doc in docs:
            try:
                metadata = getattr(doc, 'metadata', {})
                
                # Safe casting for metadata attributes
                article_raw = metadata.get('article_number')
                clause_raw = metadata.get('clause_number')
                
                article_number = int(article_raw) if article_raw is not None else None
                clause = int(clause_raw) if clause_raw is not None else None
                point = metadata.get('point') if metadata.get('is_point') else None

                extracted = extract_relevant_clause_point(article=article_number, clause=clause, point=point)
                if extracted:
                    relevant_docs.extend(extracted)
            except (ValueError, TypeError, KeyError) as e:
                logger.warning(f"Metadata extraction warning for document: {e}")
            except Exception as e:
                logger.error(f"Unexpected error extracting clause/point from doc: {e}", exc_info=True)

        # 4. Prepare Debug Metadata & Prompt
        all_docs = docs + relevant_docs
        logger.info(f"Total contextual document references: {len(all_docs)}")

        debug_json_list = []
        for doc in all_docs:
            if hasattr(doc, '__dataclass_fields__'):
                debug_json_list.append(asdict(doc))
            elif hasattr(doc, 'dict'):
                debug_json_list.append(doc.dict())
            elif isinstance(doc, dict):
                debug_json_list.append(doc)
            else:
                debug_json_list.append(str(doc))

        try:
            rag_prompt = get_rag_prompt(query, all_docs)
        except Exception as e:
            logger.error(f"Error generating RAG prompt: {e}", exc_info=True)
            rag_prompt = query

        # 5. Build Chat Messages History
        formatted_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in history:
            formatted_messages.append(msg)
        formatted_messages.append({"role": "user", "content": rag_prompt})

        # 6. Stream LLM Generation with Exception Handling
        try:
            logger.info("Starting response generation stream from LLM...")
            for in_thinking, chunk in self.llm.generate(formatted_messages, stream=True):
                if in_thinking:
                    yield debug_json_list, "", chunk
                else:
                    yield debug_json_list, chunk, ""
        except Exception as e:
            logger.error(f"Error during LLM stream generation: {e}", exc_info=True)
            yield debug_json_list, "An error occurred while generating the response.", ""

    def reset_history(self):
        logger.debug("Chat history reset triggered.")
        pass