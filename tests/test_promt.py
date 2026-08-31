from llm.chat_engine import ChatEngine
from backend.main import ChatRequest

chat = ChatRequest()

test_queries = [
    # "Hôm qua tôi vượt đèn đỏ thì có bị sao không?",
    # "Tôi chạy xe nhanh hơn tốc độ cho phép thì có bị phạt không?",
    # "Tôi đi xe máy mà không đội nón bảo hiểm thì sao?",
    "Tôi uống bia rồi lái xe về nhà thì có bị phạt không?",
    # "Tôi không có bằng lái mà vẫn chạy xe thì có sao không?",
    # "Tôi đậu xe ngay chỗ có biển cấm đỗ thì bị gì?",
    # "Tôi đi ngược chiều một đoạn ngắn thì có bị phạt không?",
    # "Tôi rẽ mà quên bật xi nhan thì có vi phạm không?",
    # "Cảnh sát giao thông yêu cầu tôi dừng xe nhưng tôi chạy tiếp thì sao?",
    # "Tôi gây tai nạn rồi bỏ đi khỏi hiện trường thì có bị xử lý không?",
]

import time

for query in test_queries:
    print(f"\nINPUT : {query}")
    thinking, content =chat.chat_generator(query=query)
    print(thinking)
    print(content)
    time.sleep(4)
