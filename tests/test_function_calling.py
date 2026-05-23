import sys
import os
import logging

# Thêm thư mục gốc vào PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm.chat_engine import ChatEngine
from core.setup_logging import setup_logging

setup_logging()
logger = logging.getLogger('test_tool')

def test_chat_with_tools():
    engine = ChatEngine()
    
    # Danh sách các câu hỏi test cho từng loại tool
    test_queries = [
        "Hôm qua tôi vượt đèn đỏ thì bị phạt bao nhiêu tiền", # Kỳ vọng gọi extract_clause_point
        "Điều 6 khoản 11 điểm c đề cập việc gì?", # Kỳ vọng gọi extract_relevant_clause_point
        "Điều 6 khoản 15 điểm b tới những quy định nào?", # Kỳ vọng gọi extract_clause_point_references
    ]
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"USER QUERY: {query}")
        print(f"{'='*50}")
        
        # Stream kết quả
        full_text = ""
        debug_info = None
        
        for debug, chunk in engine.chat(query, []):
            debug_info = debug
            if chunk:
                # In ra phần text mới (vì chunk là full response)
                new_part = chunk[len(full_text):]
                print(new_part, end="", flush=True)
                full_text = chunk
        
        print("\n\n[DEBUG INFO - RAG Documents]:")
        for i, doc in enumerate(debug_info[:2], 1): # Chỉ in 2 docs đầu cho đỡ dài
            print(f"  {i}. {doc.get('metadata', {}).get('document_title')} - {doc.get('text')[:50]}...")

if __name__ == "__main__":
    try:
        test_chat_with_tools()
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
