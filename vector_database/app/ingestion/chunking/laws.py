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
