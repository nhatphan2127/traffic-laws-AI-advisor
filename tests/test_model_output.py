import sys
import os

# Thêm đường dẫn gốc của project vào sys.path
sys.path.append(os.getcwd())

from llm.chat_engine import ChatEngine
import asyncio

async def test_chat():
    try:
        print("Đang khởi tạo ChatEngine...")
        engine = ChatEngine()
        query = "Mức phạt lỗi không đội mũ bảo hiểm là bao nhiêu?"
        history = []
        
        print(f"Gửi câu hỏi: {query}")
        
        # Vì engine.chat là generator thông thường nhưng bên trong có logic phức tạp
        # chúng ta sẽ lặp qua nó
        for docs, answer, thinking, tool_calls in engine.chat(query, history):
            if thinking:
                print(f"Thinking: {thinking[-1]}")
            if answer:
                # In ra chunk mới nhất hoặc toàn bộ answer tùy ý
                # Ở đây ta in answer để xem text có được sinh ra không
                print(f"Answer progress: {len(answer)} chars", end="\r")
        
        print("\n--- KẾT QUẢ CUỐI CÙNG ---")
        # Lấy kết quả cuối cùng từ vòng lặp
        # (docs, answer, thinking, tool_calls) ở vòng lặp cuối sẽ chứa full answer
        print(f"Câu trả lời: {answer}")
        
    except Exception as e:
        print(f"Lỗi: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_chat())
