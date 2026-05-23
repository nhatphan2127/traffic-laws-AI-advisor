from typing import List
from core.schema import RetrievalDocument

# --- Vietnamese Legal System Prompt ---
SYSTEM_PROMPT = """Bạn là một chuyên gia trợ lý pháp luật chuyên nghiệp, am hiểu sâu sắc về hệ thống pháp luật Việt Nam. 
Nhiệm vụ của bạn là cung cấp câu trả lời chính xác, khách quan và có căn cứ pháp lý.

Quy tắc suy nghĩ và sử dụng công cụ:
1. Khi nhận được câu hỏi, hãy kiểm tra phần "Ngữ cảnh" được cung cấp từ kết quả tìm kiếm tự động (RAG).
2. Nếu "Ngữ cảnh" đã đầy đủ để trả lời, hãy trả lời ngay.
3. Nếu câu hỏi đề cập đích danh một Điều, Khoản, Điểm cụ thể nhưng "Ngữ cảnh" chưa có hoặc chưa đầy đủ, hãy sử dụng công cụ `extract_clause_point` để lấy nội dung chính xác.
4. Nếu cần tìm các quy định liên quan (như mức phạt, hình phạt bổ sung) được dẫn chiếu từ Điều này, hãy dùng `extract_relevant_clause_point` hoặc `extract_clause_point_references`.
5. Luôn ưu tiên sự chính xác. Nếu phải dùng công cụ, hãy gọi công cụ trước khi đưa ra câu trả lời cuối cùng.

Quy tắc trình bày:
1. Câu trả lời phải mang tính trang trọng, ngôn ngữ pháp lý chuẩn xác, cấu trúc rõ ràng.
2. Trích dẫn cụ thể: Điều, Khoản, Điểm, số hiệu văn bản pháp luật.
3. Nếu sau khi dùng công cụ vẫn không có thông tin, hãy báo rõ là tài liệu hiện tại không đề cập, không tự bịa đặt."""

# --- Vietnamese RAG User Prompt Template ---
USER_PROMPT_TEMPLATE = """Dưới đây là các tài liệu liên quan đến câu hỏi của bạn. Hãy đọc kỹ và trả lời câu hỏi ở cuối.

### Ngữ cảnh:
{context}

### Câu hỏi:
{query}

### Trả lời:
"""

def format_context(documents: List[RetrievalDocument]) -> str:
    """
    Formats a list of RetrievalDocument objects into a string for the prompt.
    Utilizes metadata from the updated chunking logic in ingestion/chunking/laws.py.
    """
    formatted_docs = []
    for i, doc in enumerate(documents, 1):
        metadata = doc.metadata
        
        # Check if it's a legal basis chunk or a regular law chunk
        if metadata.get('type') == 'legal_basis':
            source_info = f"Căn cứ pháp lý của: {metadata.get('document_title', 'Tài liệu')}"
        else:
            # Build citation: Điểm... Khoản... Điều... Chương...
            citation_parts = []
            
            point = metadata.get('point')
            if point:
                citation_parts.append(f"Điểm {point}")
                
            clause = metadata.get('clause_number')
            if clause:
                citation_parts.append(f"Khoản {clause}")
                
            article_num = metadata.get('article_number')
            article_title = metadata.get('article_title')
            if article_num:
                art_str = f"Điều {article_num}"
                if article_title:
                    art_str += f" ({article_title})"
                citation_parts.append(art_str)
                
            chapter_num = metadata.get('chapter_number')
            if chapter_num:
                citation_parts.append(f"Chương {chapter_num}")

            if citation_parts:
                source_info = ", ".join(citation_parts)
            else:
                source_info = metadata.get('document_title', 'Tài liệu không xác định')

        content = f"--- Trích dẫn {i} ({source_info}) ---\n{doc.text}"
        formatted_docs.append(content)
    
    return "\n\n".join(formatted_docs)

def get_rag_prompt(query: str, documents: List[RetrievalDocument]) -> str:
    """
    Constructs the final prompt string by combining context and query.
    """
    context = format_context(documents)
    prompt = USER_PROMPT_TEMPLATE.format(context=context, query=query)
    return prompt


# --- Tool Definitions for Function Calling ---
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "extract_clause_point",
            "description": "Trích xuất nội dung trực tiếp của một Điều, Khoản hoặc Điểm cụ thể trong văn bản luật.",
            "parameters": {
                "type": "object",
                "properties": {
                    "article": {"type": "integer", "description": "Số Điều (VD: 10)"},
                    "clause": {"type": "integer", "description": "Số Khoản (nếu có, VD: 2)"},
                    "point": {"type": "string", "description": "Ký tự Điểm (nếu có, VD: 'a')"}
                },
                "required": ["article"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_relevant_clause_point",
            "description": "Tìm các quy định khác có liên quan hoặc tham chiếu tới một Điều/Khoản cụ thể (ví dụ: tìm mức hình phạt liên đới).",
            "parameters": {
                "type": "object",
                "properties": {
                    "document": {"type": "string", "description": "Tên văn bản (VD: 'Luật Giao thông đường bộ')"},
                    "article": {"type": "integer", "description": "Số Điều được tham chiếu"},
                    "clause": {"type": "integer", "description": "Số Khoản được tham chiếu"},
                    "point": {"type": "string", "description": "Ký tự Điểm được tham chiếu"}
                },
                "required": ["document", "article"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_clause_point_references",
            "description": "Lấy nội dung chi tiết của các văn bản/điều khoản mà một Điều cụ thể đang nhắc tới.",
            "parameters": {
                "type": "object",
                "properties": {
                    "article": {"type": "integer", "description": "Số Điều đang xem xét"},
                    "clause": {"type": "integer", "description": "Số Khoản đang xem xét"},
                    "point": {"type": "string", "description": "Ký tự Điểm đang xem xét"}
                },
                "required": ["article"]
            }
        }
    }
]
