# from typing import List, Dict
# from retrieval.retrieval import retrieval
# from llm.model import LLMModel
# from llm.promt_template import get_rag_prompt, SYSTEM_PROMPT

# class ChatEngine:
#     def __init__(self):
#         self.llm = LLMModel()
#         self.history: List[Dict[str, str]] = []

#     def _get_contextualized_query(self, query: str) -> str:
#         """
#         In a real multi-turn system, this would use the LLM to rewrite the query.
#         For now, we'll use a simpler heuristic or just the latest query to keep it fast.
#         """
#         if not self.history:
#             return query
#         return query

#     def chat(self, query: str, history: List[Dict[str, str]]) -> str:
#         """
#         history is a list of dictionaries with 'role' and 'content' keys (from Gradio).
#         """
#         # Transform history to the format expected by Qwen2-VL
#         self.history = []
#         for msg in history:
#             role = msg["role"]
#             content = msg["content"]
#             self.history.append({
#                 "role": role,
#                 "content": [{"type": "text", "text": content}]
#             })

#         # 1. Contextualize query
#         standalone_query = self._get_contextualized_query(query)

#         # 2. Retrieval
#         docs = retrieval(standalone_query)

#         # 3. Format Prompt
#         rag_prompt = get_rag_prompt(query, docs)
        
#         # Build the final messages list including history if needed
#         # For now, we follow the previous pattern but ensuring the format is correct
#         messages = [
#             {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
#             {"role": "user", "content": [{"type": "text", "text": rag_prompt}]}
#         ]

#         # 4. Generate Response
#         response = self.llm.generate(messages)
#         return response

#     def reset_history(self):
#         self.history = []


from typing import List, Dict, Generator
from dataclasses import asdict
from retrieval.retrieval import retrieval
from llm.model import LLMModel
from llm.promt_template import get_rag_prompt, SYSTEM_PROMPT

class ChatEngine:
    def __init__(self):
        self.llm = LLMModel()

    def chat(self, query: str, history: List[Dict[str, str]]) -> Generator:
        """
        history: List[Dict] dạng [{"role": "user", "content": "..."}, ...]
        """
        # 1. Retrieval - Nhận List[RetrievalDocument]
        docs = retrieval(query)
        
        # Chuyển dataclass sang dict để Gradio gr.JSON hiển thị được
        debug_json_list = [asdict(doc) for doc in docs]

        # 2. Xây dựng prompt cho LLM
        # Bắt đầu với System Prompt
        formatted_messages = [
            {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]}
        ]
        
        # Thêm lịch sử hội thoại (history đã là list các dict chuẩn rồi)
        # Chúng ta chỉ cần format lại nội dung content theo chuẩn Qwen (list of dicts)
        # for msg in history[-5:]: # Lấy 5 lượt gần nhất
        #     formatted_messages.append({
        #         "role": msg["role"],
        #         "content": [{"type": "text", "text": msg["content"]}]
        #     })

        # Thêm câu hỏi hiện tại kèm kết quả tìm kiếm (RAG)
        rag_prompt = get_rag_prompt(query, docs)
        formatted_messages.append({
            "role": "user", 
            "content": [{"type": "text", "text": rag_prompt}]
        })

        # 3. Yield JSON trích xuất trước để debug (Cột phải hiện ngay)
        yield debug_json_list, ""

        # 4. Stream kết quả từ LLM
        full_response = ""
        for chunk in self.llm.stream_generate(formatted_messages):
            full_response += chunk
            yield debug_json_list, full_response

    def reset_history(self):
        pass