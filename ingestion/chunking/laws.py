import logging
import json
import re
from pathlib import Path
import shutil
from typing import Any, Dict, List
from core.setup_logging import setup_logging
from core.load_settings import load_settings

# Initialization
settings = load_settings()
setup_logging()
logger = logging.getLogger("ingestion")

processed_dir = settings['data']['processed_dir']
raw_dir = settings['data']['raw_dir']

def get_document_short_name(file_name: str) -> str:
    """
    Parses a file name to extract a clean shorthand Vietnamese legal document code.
    E.g. 168_2024_ND-CP_619502.json -> Nghị định 168/2024/NĐ-CP
    """
    match = re.search(r"(\d+)_(\d+)_(ND-CP|NĐ-CP)", file_name, re.IGNORECASE)
    if match:
        num, year, typ = match.groups()
        return f"Nghị định {num}/{year}/NĐ-CP"
    return "Văn bản pháp luật"

# def chunk_laws() -> List[Dict[str, Any]]:
#     """
#     Parses a legal document JSON file and breaks it into smaller chunks 
#     based on Clauses and Points, incorporating nested reference metadata 
#     and context enrichment for optimal vector DB retrieval.
#     """
#     # 1. Configuration and Path Setup
#     processed_dir = settings.get('data', {}).get('processed_dir', 'data/processed')
#     file_name = '168_2024_ND-CP_619502.json'
#     file_path = Path(processed_dir) / file_name

#     chunks: List[Dict[str, Any]] = []
    
#     logger.info(f"Starting chunking process for: {file_path}")

#     # 2. File Access and Validation
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
#     doc_short_name = get_document_short_name(file_name)
#     chapters = data.get('chapters', [])
    
#     if not chapters:
#         logger.warning(f"No chapters found in document: '{document_title}'")
#     else:
#         logger.info(f"Processing document file: {file_path} ({len(chapters)} chapters found)")

#     # 3. Iterate through Chapters
#     for idx, chapter in enumerate(chapters):
#         chapter_title: str = chapter.get('chapter_title', 'No Title')
#         chapter_number: int = chapter.get('chapter_number')
#         articles: list[dict] = chapter.get('articles', [])

#         chapter_context = f"Chương {chapter_number if chapter_number is not None else idx}"
#         chapter_header = f"{chapter_context}: {chapter_title}"
        
#         if not articles:
#             logger.warning(f"{chapter_header} contains no articles. Skipping.")
#             continue

#         # 4. Iterate through Articles
#         for art_idx, article in enumerate(articles):
#             article_title: str = article.get('article_title', '')
#             article_number: int = article.get('article_number', None)
#             article_category: str = article.get('category', '')
#             clauses: list[dict] = article.get('clauses', [])

#             article_context = f"Điều {article_number if article_number is not None else art_idx}"

#             if not article_title:
#                 logger.debug(f"{article_context} in {chapter_header} is missing a title.")

#             # 5. Iterate through Clauses
#             for clause_idx, clause in enumerate(clauses):
#                 clause_number: int = clause.get('clause_number', None)
#                 clause_content: str = clause.get('content', '').strip()
#                 points: list[dict] = clause.get('points', [])
#                 clause_references: list[dict] = clause.get('references', [])

#                 clause_context_str = f"Khoản {clause_number if clause_number is not None else clause_idx}"

#                 # Base metadata tracking structural lineage
#                 base_metadata = {
#                     "document_title": document_title,
#                     "document_short_name": doc_short_name,
#                     "chapter_number": chapter_number,
#                     "chapter_title": chapter_title, 
#                     "article_number": article_number,
#                     "article_title": article_title,
#                     "article_category": article_category,
#                     "clause_number": clause_number
#                 }

#                 # Construct rich hierarchical path prefix for the text representation
#                 text_prefix_lines = [
#                     f"[Văn bản: {doc_short_name}]",
#                     f"[{chapter_header}]",
#                     f"[{article_title}]"
#                 ]
#                 text_prefix = "\n".join(text_prefix_lines)

#                 # Case A: Clause has no sub-points -> Treat whole clause as one chunk
#                 if not points:
#                     if clause_content:
#                         # Vector text includes standard Vietnamese hierarchical headers for optimal semantic context
#                         clause_label = f"Khoản {clause_number}: " if clause_number is not None else ""
#                         enriched_text = f"{text_prefix}\n{clause_label}{clause_content}"
                        
#                         chunks.append({
#                             "text": enriched_text,
#                             "metadata": {
#                                 **base_metadata,
#                                 "is_point": False,
#                                 "point": None,
#                                 "references": clause_references
#                             }
#                         })
#                     else:
#                         logger.debug(f"Empty content found at {article_context}, {clause_context_str}. Skipping chunk creation.")

#                 # Case B: Clause contains points -> Treat each point as a separate chunk
#                 else:
#                     logger.debug(f"Processing {len(points)} points under {article_context}, {clause_context_str}")
#                     for p in points:
#                         point_label: str = p.get("point", '')
#                         point_content: str = p.get("content", '').strip()
#                         point_references: list[dict] = p.get("references", [])

#                         if point_content:
#                             # Context Enrichment: Include document, chapter, article, parent clause, and child point
#                             clause_label = f"Khoản {clause_number}: " if clause_number is not None else ""
#                             clause_part = f"{clause_label}{clause_content}" if clause_content else ""
                            
#                             point_part = f"Điểm {point_label}: {point_content}"
                            
#                             # Merge prefix with clause context and the specific point details
#                             enriched_point_text = f"{text_prefix}\n{clause_part}\n{point_part}".strip()
                            
#                             # Combine clause-level and point-level references if necessary, or keep separate
#                             # Here we prioritize point references, falling back to clause references if empty
#                             active_references = point_references if point_references else clause_references

#                             chunks.append({
#                                 "text": enriched_point_text,
#                                 "metadata": {
#                                     **base_metadata,
#                                     "is_point": True,
#                                     "point": point_label,
#                                     "references": active_references 
#                                 }
#                             })
#                         else:
#                             logger.warning(f"Found point structure with empty content under {article_context}, {clause_context_str}")

#     # 6. Add Legal Basis as a standalone chunk
#     legal_basis = data.get('legal_basis', '')
#     if legal_basis:
#         total_articles = sum(len(c.get('articles', [])) for c in chapters)
#         chunks.append({
#             "text": f"[Văn bản: {doc_short_name}]\nCăn cứ pháp lý của văn bản:\n{legal_basis}", 
#             "metadata": {
#                 "type": "legal_basis",
#                 "document_title": document_title,
#                 "document_short_name": doc_short_name,
#                 "chapter_total": len(chapters),
#                 "article_total": total_articles,
#                 "references": []
#             }
#         })

#     logger.info(f"Chunking complete. Generated {len(chunks)} chunks from file: '{file_path}'.")
#     return chunks


def transport_files():
    raw_folder = Path(raw_dir)

    for folder in raw_folder.iterdir():
        if not folder.is_dir():
            continue

        source = folder / "data.json"

        if not source.exists():
            print(f"File not found: {source}")
            continue

        with source.open("r", encoding="utf-8") as file:
            data = json.load(file)

        document_name = data["document"]

        # Replace "/" with "_"
        document_name = f"{document_name.replace("/", "_")}.json"

        destination = Path(processed_dir) / document_name

        if source.exists():
            shutil.copy(source, destination)
            print(f"Copied: {source} -> {destination}")
        else:
            print(f"Source file not found: {source}")


def chunk_laws() -> List[Dict[str, Any]]:
    """
    Parses all legal document JSON files in processed_dir and breaks them
    into smaller chunks based on Clauses and Points.
    """
    processed_folder = Path(processed_dir)
    chunks: List[Dict[str, Any]] = []

    # Sử dụng glob để chỉ lấy file .json
    for file_path in processed_folder.glob("*.json"):
        logger.info(f"Starting chunking process for: {file_path}")

        # 1. Read JSON file
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read/parse JSON '{file_path}': {e}")
            continue

        if not isinstance(data, dict):
            logger.error(f"Invalid JSON in '{file_path}'. Root must be a dict.")
            continue

        doc_title = data.get("document_title", "Untitled Document")
        doc_short_name = data.get("document", "")  # Fixed syntax error from data.get['document']
        chapters = data.get("chapters", [])

        if not chapters:
            logger.warning(f"No chapters found in document: '{doc_title}'")
        else:
            logger.info(f"Processing '{file_path}' ({len(chapters)} chapters)")

        # 2. Iterate through Chapters & Articles
        for c_idx, chap in enumerate(chapters):
            chap_num = chap.get("chapter_number")
            chap_title = chap.get("chapter_title", "No Title")
            chap_hdr = f"Chương {chap_num if chap_num is not None else c_idx}: {chap_title}"
            articles = chap.get("articles", [])

            if not articles:
                logger.warning(f"{chap_hdr} contains no articles. Skipping.")
                continue

            for a_idx, art in enumerate(articles):
                art_title = art.get("article_title", "")
                art_num = art.get("article_number")
                art_cat = art.get("category", "")
                clauses = art.get("clauses", [])

                prefix = f"[Văn bản: {doc_short_name}]\n[{chap_hdr}]\n[{art_title}]"
                base_meta = {
                    "document_title": doc_title,
                    "document_short_name": doc_short_name,
                    "chapter_number": chap_num,
                    "chapter_title": chap_title,
                    "article_number": art_num,
                    "article_title": art_title,
                    "article_category": art_cat,
                }

                # 3. Iterate through Clauses
                for cl_idx, cl in enumerate(clauses):
                    cl_num = cl.get("clause_number")
                    cl_content = cl.get("content", "").strip()
                    points = cl.get("points", [])
                    cl_refs = cl.get("references", [])

                    cl_label = f"Khoản {cl_num}: " if cl_num is not None else ""
                    cl_meta = {**base_meta, "clause_number": cl_num}

                    # Case A: Clause HAS NO points
                    if not points:
                        if cl_content:
                            chunks.append({
                                "text": f"{prefix}\n{cl_label}{cl_content}",
                                "metadata": {
                                    **cl_meta,
                                    "is_point": False,
                                    "point": None,
                                    "references": cl_refs,
                                },
                            })
                        else:
                            logger.debug(f"Empty content at Điều {art_num}, Khoản {cl_num}. Skipping.")

                    # Case B: Clause HAS points
                    else:
                        cl_part = f"{cl_label}{cl_content}" if cl_content else ""

                        for p in points:
                            p_label = p.get("point", "")
                            p_content = p.get("content", "").strip()
                            p_refs = p.get("references", [])

                            if not p_content:
                                logger.warning(f"Empty point content at Điều {art_num}, Khoản {cl_num}")
                                continue

                            text_parts = [prefix, cl_part, f"Điểm {p_label}: {p_content}"]
                            enriched_text = "\n".join(filter(None, text_parts)).strip()

                            chunks.append({
                                "text": enriched_text,
                                "metadata": {
                                    **cl_meta,
                                    "is_point": True,
                                    "point": p_label,
                                    "references": p_refs or cl_refs, # Ưu tiên point reference, nếu trống dùng clause reference
                                },
                            })

        # 4. Add Legal Basis
        if legal_basis := data.get("legal_basis", ""):
            total_articles = sum(len(c.get("articles", [])) for c in chapters)
            chunks.append({
                "text": f"[Văn bản: {doc_short_name}]\nCăn cứ pháp lý của văn bản:\n{legal_basis}",
                "metadata": {
                    "type": "legal_basis",
                    "document_title": doc_title,
                    "document_short_name": doc_short_name,
                    "chapter_total": len(chapters),
                    "article_total": total_articles,
                    "references": [],
                },
            })

        logger.info(f"Chunking complete for '{file_path}'. Total chunks so far: {len(chunks)}")

    return chunks
