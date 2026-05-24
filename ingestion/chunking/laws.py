# import logging
# import json
# from pathlib import Path
# from typing import Any, Dict, List

# # Internal module imports
# from core.setup_logging import setup_logging
# from core.load_settings import load_settings

# # Initialization
# settings = load_settings()
# setup_logging()
# logger = logging.getLogger("ingestion")

# def chunk_laws() -> List[Dict[str, Any]]:
#     """
#     Parses a legal document JSON file and breaks it into smaller chunks 
#     based on Clauses and Points for vector database indexing.
#     """
#     # 1. Configuration and Path Setup
#     processed_dir = settings.get('data', {}).get('processed_dir', 'data/processed')
#     file_name = '168_2024_ND-CP_619502.json'
#     file_path = Path(processed_dir) / file_name

#     chunks: List[Dict[str, Any]] = []
    
#     logger.info(f"Starting chunking process for: {file_path}")

#     # 2. File Access Validation
#     if not file_path.exists():
#         logger.error(f"File not found at path: {file_path}")
#         return chunks

#     try:
#         with open(file_path, 'r', encoding='utf-8') as file:
#             data = json.load(file)
#     except json.JSONDecodeError as e:
#         logger.error(f"Failed to parse JSON (Invalid format): {e}")
#         return chunks
#     except Exception as e:
#         logger.error(f"Unexpected error reading file: {e}")
#         return chunks
    
#     if not isinstance(data, dict):
#         logger.error("Invalid JSON structure: Root element must be a dictionary.")
#         return chunks

#     document_title = data.get('document_title', 'Untitled Document')
#     chapters = data.get('chapters', [])
    
#     if not chapters:
#         logger.warning(f"No chapters found in document: '{document_title}'")
#     else:
#         logger.info(f"Processing document file: {file_path} ({len(chapters)} chapters found)")

#     # 3. Iterate through Chapters
#     for idx, chapter in enumerate(chapters):
#         chapter_title:str = chapter.get('chapter_title', 'No Title')
#         chapter_number:int = chapter.get('chapter_number')
#         articles:list[dict] = chapter.get('articles', [])

#         # Context string for precise logging
#         chapter_context = f"Chapter {chapter_number if chapter_number else idx}"
        
#         if not articles:
#             logger.warning(f"{chapter_context} contains no articles. Skipping.")
#             continue

#         # 4. Iterate through Articles
#         for art_idx, article in enumerate(articles):
#             article_title:str = article.get('article_title', '')
#             article_number:int = article.get('article_number', None)
#             article_category:str = article.get('category', '')
#             clauses:list[dict] = article.get('clauses', [])

#             article_context = f"Article {article_number if article_number else art_idx}"

#             if not article_title:
#                 logger.debug(f"{article_context} in {chapter_context} is missing a title.")

#             # 5. Iterate through Clauses and Points
#             for clause in clauses:
#                 clause_number:int = clause.get('clause_number', None)
#                 content = clause.get('content', '').strip()
#                 points:list[dict] = clause.get('points', [])

#                 # Prepare common metadata for all chunks in this article
#                 base_metadata = {
#                     "chapter_number": chapter_number,
#                     "chapter_title": chapter_title, 
#                     "article_number": article_number,
#                     "article_title": article_title,
#                     "article_category": article_category,
#                     "clause_number": clause_number
#                 }

#                 if not points:
#                     # Case A: Clause has no sub-points, treat the whole clause as one chunk
#                     if content:
#                         chunks.append({
#                             "text": content, 
#                             "metadata": {**base_metadata, "is_point": False}
#                         })
#                 else:
#                     # Case B: Clause contains points, treat each point as a separate chunk
#                     for p in points:
#                         point_label = p.get("point", '')
#                         point_content = p.get("content", '')
#                         if point_content:
#                             chunks.append({
#                                 "text": point_content, 
#                                 "metadata": {
#                                     **base_metadata, 
#                                     "is_point": True,
#                                     "point": point_label
#                                 }
#                             })

#     # 6. Add Legal Basis as a standalone chunk
#     legal_basis = data.get('legal_basis', '')
#     if legal_basis:
#         # Calculate total articles across all chapters for metadata
#         total_articles = sum(len(c.get('articles', [])) for c in chapters)
        
#         chunks.append({
#             "text": legal_basis, 
#             "metadata": {
#                 "type": "legal_basis",
#                 "document_title": document_title,
#                 "chapter_total": len(chapters),
#                 "article_total": total_articles
#             }
#         })

#     logger.info(f"Chunking complete. Generated {len(chunks)} chunks from file: '{file_path}'.")
#     return chunks

import logging
import json
from pathlib import Path
from typing import Any, Dict, List

# Internal module imports (kept as per your environment)
from core.setup_logging import setup_logging
from core.load_settings import load_settings

# Initialization
settings = load_settings()
setup_logging()
logger = logging.getLogger("ingestion")

def chunk_laws() -> List[Dict[str, Any]]:
    """
    Parses a legal document JSON file and breaks it into smaller chunks 
    based on Clauses and Points, incorporating nested reference metadata 
    and context enrichment for optimal vector DB retrieval.
    """
    # 1. Configuration and Path Setup
    processed_dir = settings.get('data', {}).get('processed_dir', 'data/processed')
    file_name = '168_2024_ND-CP_619502.json'
    file_path = Path(processed_dir) / file_name

    chunks: List[Dict[str, Any]] = []
    
    logger.info(f"Starting chunking process for: {file_path}")

    # 2. File Access and Validation
    if not file_path.exists():
        logger.error(f"File not found at path: {file_path}")
        return chunks

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON (Invalid format): {e}")
        return chunks
    except Exception as e:
        logger.error(f"Unexpected error reading file: {e}")
        return chunks
    
    if not isinstance(data, dict):
        logger.error("Invalid JSON structure: Root element must be a dictionary.")
        return chunks

    document_title = data.get('document_title', 'Untitled Document')
    chapters = data.get('chapters', [])
    
    if not chapters:
        logger.warning(f"No chapters found in document: '{document_title}'")
    else:
        logger.info(f"Processing document file: {file_path} ({len(chapters)} chapters found)")

    # 3. Iterate through Chapters
    for idx, chapter in enumerate(chapters):
        chapter_title: str = chapter.get('chapter_title', 'No Title')
        chapter_number: int = chapter.get('chapter_number')
        articles: list[dict] = chapter.get('articles', [])

        chapter_context = f"Chapter {chapter_number if chapter_number is not None else idx}"
        
        if not articles:
            logger.warning(f"{chapter_context} ('{chapter_title}') contains no articles. Skipping.")
            continue

        # 4. Iterate through Articles
        for art_idx, article in enumerate(articles):
            article_title: str = article.get('article_title', '')
            article_number: int = article.get('article_number', None)
            article_category: str = article.get('category', '')
            clauses: list[dict] = article.get('clauses', [])

            article_context = f"Article {article_number if article_number is not None else art_idx}"

            if not article_title:
                logger.debug(f"{article_context} in {chapter_context} is missing a title.")

            # 5. Iterate through Clauses
            for clause_idx, clause in enumerate(clauses):
                clause_number: int = clause.get('clause_number', None)
                clause_content: str = clause.get('content', '').strip()
                points: list[dict] = clause.get('points', [])
                clause_references: list[dict] = clause.get('references', [])

                clause_context_str = f"Clause {clause_number if clause_number is not None else clause_idx}"

                # Base metadata tracking structural lineage
                base_metadata = {
                    "document_title": document_title,
                    "chapter_number": chapter_number,
                    "chapter_title": chapter_title, 
                    "article_number": article_number,
                    "article_title": article_title,
                    "article_category": article_category,
                    "clause_number": clause_number
                }

                # Context Enrichment: Pre-building parent strings to pass down to chunks
                parent_text_prefix = f"{article_title}\n"
                if clause_content and points:
                    # If it has points, the clause content acts as the introductory preamble
                    parent_text_prefix += f"Khung hình phạt/Quy định: {clause_content}\n"

                # Case A: Clause has no sub-points -> Treat whole clause as one chunk
                if not points:
                    if clause_content:
                        # Vector text includes the article title for semantic context
                        enriched_text = f"{article_title}\n{clause_content}"
                        
                        chunks.append({
                            "text": enriched_text,
                            "metadata": {
                                "point": "-1",
                                # ADD mấy cái kia cũng v
                                **base_metadata,
                                "is_point": False,
                                "references": clause_references # Serialized to ensure VectorDB compatibility
                            }
                        })
                    else:
                        logger.debug(f"Empty content found at {article_context}, {clause_context_str}. Skipping chunk creation.")

                # Case B: Clause contains points -> Treat each point as a separate chunk
                else:
                    logger.debug(f"Processing {len(points)} points under {article_context}, {clause_context_str}")
                    for p in points:
                        point_label: str = p.get("point", '')
                        point_content: str = p.get("content", '').strip()
                        point_references: list[dict] = p.get("references", [])

                        if point_content:
                            # Context Enrichment: Merging parent headers with child details
                            enriched_point_text = f"{parent_text_prefix}Chi tiết ({point_label}): {point_content}"
                            
                            # Combine clause-level and point-level references if necessary, or keep separate
                            # Here we prioritize point references, falling back to clause references if empty
                            active_references = point_references if point_references else clause_references

                            chunks.append({
                                "text": enriched_point_text,
                                "metadata": {
                                    **base_metadata,
                                    "is_point": True,
                                    "point": point_label,
                                    "references": active_references 
                                }
                            })
                        else:
                            logger.warning(f"Found point structure with empty content under {article_context}, {clause_context_str}")

    # 6. Add Legal Basis as a standalone chunk
    legal_basis = data.get('legal_basis', '')
    if legal_basis:
        total_articles = sum(len(c.get('articles', [])) for c in chapters)
        chunks.append({
            "text": f"Căn cứ pháp lý của văn bản:\n{legal_basis}", 
            "metadata": {
                "type": "legal_basis",
                "document_title": document_title,
                "chapter_total": len(chapters),
                "article_total": total_articles,
                "references": []
            }
        })

    logger.info(f"Chunking complete. Generated {len(chunks)} chunks from file: '{file_path}'.")
    return chunks