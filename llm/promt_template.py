from typing import List
from core.schema import RetrievalDocument

# --- Vietnamese Legal System Prompt ---
SYSTEM_PROMPT = """Bạn là một chuyên gia trợ lý pháp luật chuyên nghiệp, am hiểu sâu sắc về hệ thống pháp luật Việt Nam. 
Nhiệm vụ của bạn là cung cấp câu trả lời chính xác, khách quan và có căn cứ pháp lý dựa trên các tài liệu được cung cấp.

Quy tắc ứng xử:
1. Chỉ sử dụng thông tin trong phần "Ngữ cảnh" được cung cấp để trả lời.
2. Nếu thông tin trong "Ngữ cảnh" không đủ để trả lời câu hỏi, hãy trả lời rằng bạn không biết hoặc thông tin hiện tại không đề cập đến vấn đề này, đừng tự ý tạo ra câu trả lời.
3. Câu trả lời phải mang tính trang trọng, ngôn ngữ pháp lý chuẩn xác, cấu trúc rõ ràng.
4. Trích dẫn cụ thể (nếu có trong ngữ cảnh) như: Điều, Khoản, Điểm, số hiệu văn bản pháp luật.
5. Tuyệt đối không đưa ra ý kiến cá nhân hoặc các lời khuyên pháp lý ngoài phạm vi tài liệu."""

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
    """
    formatted_docs = []
    for i, doc in enumerate(documents, 1):
        # We can include metadata if it contains document names or dates
        doc_source = doc.metadata.get('document_title', 'Tài liệu không xác định')
        content = f"--- Tài liệu {i} (Nguồn: {doc_source}) ---\n{doc.text}"
        formatted_docs.append(content)
    
    return "\n\n".join(formatted_docs)

def get_rag_prompt(query: str, documents: List[RetrievalDocument]) -> str:
    """
    Constructs the final prompt string by combining context and query.
    """
    context = format_context(documents)
    prompt = USER_PROMPT_TEMPLATE.format(context=context, query=query)
    return prompt
