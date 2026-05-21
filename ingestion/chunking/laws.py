import logging
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Import modules của bạn
from core.setup_logging import setup_logging
from core.load_settings import load_settings

# Khởi tạo
settings = load_settings()
setup_logging()
logger = logging.getLogger("ingestion")

def chunk_laws() -> List[Dict[str, Any]]:
    file_path = Path(settings['data']['processed_dir']) / '168_2024_ND-CP_619502.json'
    file_path = Path(file_path)

    chunks: List[Dict[str, Any]] = []
    
    # Đọc file JSON an toàn
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except Exception as e:
        logger.error(f"Failed to read or parse JSON file {file_path}: {e}")
        return chunks
    
    if not isinstance(data, dict):
        logger.error("Invalid JSON format: Root element must be a dictionary.")
        return chunks

    document_title = data.get('document_title', '')
    chapters = data.get('chapters', [])
    
    if not chapters:
        logger.warning(f"No chapters found in document '{document_title}'")
        return chunks
    
    for chapter in chapters:
        chapter_title = chapter.get('chapter_title', '')
        
        for article in chapter.get('articles', []):
            article_title = article.get('article_title', '')
            article_number = article.get('article_number', '')

            for clause in article.get('clauses', []):
                clause_number = clause.get('clause_number', '')
                content = clause.get('content', '').strip()
                
                points_list = []
                for point in clause.get('points', []):
                    p_num = point.get('point', '')
                    p_content = point.get('content', '').strip()
                    if p_num or p_content:
                        points_list.append(f"({p_num}) {p_content}".strip())
                
                if not content and not points_list:
                    logger.debug(f"Empty clause skipped: Article {article_number}, Clause {clause_number}")
                    continue

                text_parts = [article_title]
                if content:
                    text_parts.append(content)
                if points_list:
                    text_parts.extend(points_list)
                
                final_text = "\n".join(text_parts).strip()

                # Ghi nhận chunk
                chunks.append({
                    "text": final_text, 
                    "metadata": {
                        'document_title': document_title.capitalize(),
                        'chapter_title': chapter_title.capitalize(),
                        'category': chapter.get('category', ''),
                        'article_number': article_number,
                        # 'article_title': article_title,
                        'clause_number': clause_number
                    }
                })

    chunks.append({
                    "text": data.get('legal_basis', ''), 
                    "metadata": {
                        'document_title': document_title.capitalize(),
                    }
                })
    return chunks