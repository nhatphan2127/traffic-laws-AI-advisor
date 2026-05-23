from vectorstore.qdrant import get_qdrant_client, ensure_collection
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue, Record
from core.setup_logging import setup_logging
from core.load_settings import load_settings

setup_logging()
logger = logging.getLogger('functions')
settings = load_settings()

VECTOR_DB_SETTINGS = settings['vector_database']
VECTOR_DB_COLLECTION = VECTOR_DB_SETTINGS.get("collection_name", "default_collection")


def extract_relevant_clause_point(document: str, article: int, clause: int = None, point: str = None) -> list[Record]:
    """
    Hàm 1: Tìm tất cả các Điều/Khoản khác có nội dung tham chiếu (reference) 
    tới một document, article, clause, point cụ thể. (VD: Tìm hình phạt liên đới)
    """
    _client: QdrantClient = get_qdrant_client()
    ensure_collection(_client)
    
    if not article:
        logger.error(f"Can not extract missing article.")
        return []

    # Khởi tạo các điều kiện bắt buộc phải có
    must_conditions = [
        FieldCondition(key="references[].document", match=MatchValue(value=document)),
        FieldCondition(key="references[].article", match=MatchValue(value=article))
    ]

    # Append linh hoạt các điều kiện nhỏ hơn
    if clause is not None:
        must_conditions.append(FieldCondition(key="references[].clause", match=MatchValue(value=clause)))
    if point is not None:
        must_conditions.append(FieldCondition(key="references[].point", match=MatchValue(value=point)))

    scroll_filter = Filter(must=must_conditions)

    results, _ = _client.scroll(
        collection_name=VECTOR_DB_COLLECTION,
        scroll_filter=scroll_filter,
        limit=50 # Nên có limit để tránh tràn kết quả
    )
    
    logger.info(f"Hàm 1 - Filtered {len(results)} items referencing {document} Article {article}")
    return results


def extract_clause_point(article: int, clause: int = None, point: str = None) -> list[Record]:
    """
    Hàm 2: Trích xuất nội dung trực tiếp của một Điều, Khoản hoặc Điểm cụ thể.
    """
    _client: QdrantClient = get_qdrant_client()
    ensure_collection(_client)
    
    if not article:
        logger.error(f"Can not extract missing article.")
        return []

    must_conditions = [
        FieldCondition(key="article_number", match=MatchValue(value=article))
    ]

    if clause is not None:
        must_conditions.append(FieldCondition(key="clause_number", match=MatchValue(value=clause)))
    if point is not None:
        must_conditions.append(FieldCondition(key="point", match=MatchValue(value=point)))

    scroll_filter = Filter(must=must_conditions)

    results, _ = _client.scroll(
        collection_name=VECTOR_DB_COLLECTION,
        scroll_filter=scroll_filter,
        limit=50
    )
    
    logger.info(f"Hàm 2 - Filtered {len(results)} items from exact structural search.")
    return results


def extract_clause_point_references(article: int, clause: int = None, point: str = None) -> list[Record]:
    """
    Hàm 3: Lấy NỘI DUNG THỰC TẾ của những Điều/Khoản/Điểm mà một 
    nhóm chunks (Điều/Khoản/Điểm mục tiêu) đang tham chiếu tới.
    """
    _client: QdrantClient = get_qdrant_client()
    ensure_collection(_client)
    
    if not article:
        logger.error(f"Can not extract references for missing article.")
        return []

    # BƯỚC 1: Tìm TẤT CẢ các chunks đại diện cho Điều/Khoản/Điểm được yêu cầu
    must_conditions = [
        FieldCondition(key="article_number", match=MatchValue(value=article))
    ]
    if clause is not None:
        must_conditions.append(FieldCondition(key="clause_number", match=MatchValue(value=clause)))
    if point is not None:
        must_conditions.append(FieldCondition(key="point", match=MatchValue(value=point)))

    # Thay limit=1 thành limit đủ lớn (VD: 100) để lấy được toàn bộ Điểm/Khoản của 1 Điều
    source_records, _ = _client.scroll(
        collection_name=VECTOR_DB_COLLECTION,
        scroll_filter=Filter(must=must_conditions),
        limit=100 
    )
    
    if not source_records:
        logger.error(f"No records found for Article {article}, Clause {clause}, Point {point}")
        return []

    # BƯỚC 2: Thu thập và gom nhóm toàn bộ references từ TẤT CẢ các source chunks
    unique_references = {}
    
    for record in source_records:
        refs = record.payload.get("references", [])
        for r in refs:
            # Rút trích thông tin tham chiếu
            ref_doc = r.get("document", "")
            ref_article = r.get("article")
            ref_clause = r.get("clause")
            ref_point = r.get("point")
            
            # Bỏ qua nếu tham chiếu không chỉ định được Điều (không đủ đk truy xuất)
            if not ref_article:
                continue
                
            # Tạo một khóa (key) duy nhất để chống trùng lặp (Deduplicate)
            # VD: Cùng tham chiếu về Điều 10 Khoản 2 thì chỉ lưu 1 lần
            ref_key = f"{ref_doc}_{ref_article}_{ref_clause}_{ref_point}"
            unique_references[ref_key] = r

    if not unique_references:
        logger.info(f"Các chunks của Điều {article} không chứa bất kỳ tham chiếu nào.")
        return []

    # BƯỚC 3: Dùng danh sách references (đã lọc trùng) đi query lại vào DB
    referenced_chunks = []
    
    for ref in unique_references.values():
        ref_article = ref.get("article")
        ref_clause = ref.get("clause")
        ref_point = ref.get("point")

        ref_conditions = [
            FieldCondition(key="article_number", match=MatchValue(value=ref_article))
        ]
        
        if ref_clause is not None:
            ref_conditions.append(FieldCondition(key="clause_number", match=MatchValue(value=ref_clause)))
        if ref_point is not None:
            ref_conditions.append(FieldCondition(key="point", match=MatchValue(value=ref_point)))

        # Kéo toàn bộ các chunks của điều khoản được tham chiếu
        ref_records, _ = _client.scroll(
            collection_name=VECTOR_DB_COLLECTION,
            scroll_filter=Filter(must=ref_conditions),
            limit=100
        )
        
        referenced_chunks.extend(ref_records)

    # BƯỚC 4: Loại bỏ các target chunk bị trùng lặp 
    # (Trường hợp lệnh query của Qdrant trả về các chunk chồng chéo nhau)
    unique_chunks_dict = {record.id: record for record in referenced_chunks}
    unique_chunks = list(unique_chunks_dict.values())

    logger.info(f"Hàm 3 - Đã gộp {len(source_records)} chunks nguồn -> Tìm thấy {len(unique_references)} references khác nhau -> Trích xuất thành công {len(unique_chunks)} chunks đích.")
    
    return unique_chunks


def format_records_for_llm(records: list[Record]) -> str:
    """
    Chuyển đổi danh sách Record từ Qdrant sang chuỗi văn bản dễ đọc cho LLM.
    """
    if not records:
        return "Không tìm thấy dữ liệu phù hợp."
    
    formatted_texts = []
    for i, rec in enumerate(records, 1):
        payload = rec.payload
        # Trích xuất citation
        citation = []
        if payload.get("point"): citation.append(f"Điểm {payload['point']}")
        if payload.get("clause_number"): citation.append(f"Khoản {payload['clause_number']}")
        if payload.get("article_number"): citation.append(f"Điều {payload['article_number']}")
        if payload.get("article_title"): citation.append(f"({payload['article_title']})")
        
        source = ", ".join(citation) if citation else payload.get("document_title", "Tài liệu")
        text = payload.get("text", "")
        formatted_texts.append(f"--- Kết quả {i} ({source}) ---\n{text}")
        
    return "\n\n".join(formatted_texts)
