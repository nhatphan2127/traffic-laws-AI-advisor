from typing import List
from core.schema import RetrievalDocument

# --- Vietnamese Legal System Prompt ---
SYSTEM_PROMPT = """Bạn là một chuyên gia trợ lý pháp luật chuyên nghiệp, am hiểu sâu sắc về hệ thống pháp luật Việt Nam. 
Nhiệm vụ của bạn là cung cấp câu trả lời chính xác, khách quan và có căn cứ pháp lý.

Quy tắc suy nghĩ và sử dụng công cụ:
1. Khi nhận được câu hỏi, hãy kiểm tra phần "Ngữ cảnh" được cung cấp từ kết quả tìm kiếm tự động (RAG).
2. Nếu "Ngữ cảnh" đã đầy đủ để trả lời, hãy trả lời ngay.
3. Luôn ưu tiên sự chính xác.

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


# --- Legal Query Normalization Prompt ---
LEGAL_QUERY_NORMALIZATION_PROMPT = """Bạn là một chuyên gia xử lý truy vấn pháp luật cho hệ thống Information Retrieval (IR) và RAG.

Nhiệm vụ của bạn là chuyển câu hỏi của người dùng thành một truy vấn pháp lý có ý nghĩa tương đương, sử dụng các thuật ngữ pháp lý phù hợp để hệ thống Retrieval có thể tìm chính xác các văn bản pháp luật liên quan.

Mục tiêu
Người dùng có thể sử dụng ngôn ngữ đời thường, ví dụ: "Thường thì khi tôi vượt đèn đỏ thì có bị gì không?"
Bạn phải xác định hành vi pháp lý được mô tả và chuyển nó thành cách diễn đạt phù hợp với văn bản pháp luật.
Ví dụ: "vượt đèn đỏ" -> "không chấp hành tín hiệu của đèn giao thông" hoặc -> "không tuân thủ hiệu lệnh của đèn tín hiệu giao thông"

Quy tắc
- Xác định hành vi pháp lý chính trong câu hỏi.
- Chuyển cách diễn đạt đời thường thành thuật ngữ pháp lý phổ biến.
- Giữ nguyên đối tượng thực hiện hành vi nếu được đề cập.
- Giữ nguyên phương tiện, đối tượng bị tác động, địa điểm, thời gian, mức độ hoặc các điều kiện khác nếu có.
- Không tự suy đoán tội danh nếu người dùng chỉ mô tả hành vi.
- Không tự thêm số điều, khoản hoặc văn bản pháp luật.
- Không thay đổi bản chất của hành vi.
- Không thêm thông tin không có trong câu hỏi.
- Ưu tiên thuật ngữ có khả năng xuất hiện trong văn bản pháp luật.
- Có thể thay thế từ ngữ đời thường bằng thuật ngữ pháp lý tương đương nếu điều đó giúp Retrieval tìm đúng văn bản.
- Không trả lời câu hỏi pháp luật. Chỉ tạo truy vấn dùng cho Retrieval.

Ví dụ
Input: "Thường thì khi tôi vượt đèn đỏ thì có bị gì không?"
Output: "Không chấp hành tín hiệu của đèn tín hiệu giao thông có bị xử phạt không?"

Input: "Tôi đi xe máy không đội mũ bảo hiểm thì sao?"
Output: "Người điều khiển xe mô tô, xe gắn máy không đội mũ bảo hiểm có bị xử phạt không?"

Input: "Tôi lấy đồ của người khác mà không được phép thì có phạm luật không?"
Output: "Chiếm đoạt tài sản của người khác trái phép có bị xử lý theo pháp luật không?"

Input: "Tôi chạy xe quá tốc độ thì bị phạt thế nào?"
Output: "Điều khiển phương tiện giao thông vượt quá tốc độ quy định có bị xử phạt như thế nào?"

Output
Chỉ trả về một câu truy vấn pháp lý đã được chuẩn hóa.
- Không giải thích.
- Không trả lời câu hỏi.
- Không đưa ra điều luật.
- Không đưa ra mức phạt.

INPUT:
{USER_QUERY}

OUTPUT:"""