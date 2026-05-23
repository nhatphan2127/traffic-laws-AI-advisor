import json
import logging
from typing import List, Dict, Generator
from dataclasses import asdict
from retrieval.retrieval import retrieval
from llm.model import LLMModel
from llm.promt_template import get_rag_prompt, SYSTEM_PROMPT, TOOLS
from functions.qdrant_filter import (
    extract_clause_point, 
    extract_relevant_clause_point, 
    extract_clause_point_references,
    format_records_for_llm
)

logger = logging.getLogger('chat_engine')

class ChatEngine:
    def __init__(self):
        self.llm = LLMModel()

    def chat(self, query: str, history: List[Dict[str, str]]) -> Generator:
        """
        history: List[Dict] dạng [{"role": "user", "content": "..."}, ...]
        """
        # 1. RAG Retrieval ban đầu
        docs = retrieval(query)
        debug_json_list = [asdict(doc) for doc in docs]

        # 2. Xây dựng prompt cho LLM
        formatted_messages = [
            {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]}
        ]
        
        # (Optional: Thêm history ở đây nếu cần)

        rag_prompt = get_rag_prompt(query, docs)
        formatted_messages.append({
            "role": "user", 
            "content": [{"type": "text", "text": rag_prompt}]
        })

        # Yield kết quả tìm kiếm sơ bộ
        yield debug_json_list, "Đang suy nghĩ..."

        # 3. Vòng lặp kiểm tra Function Calling
        logger.info(f"🔍 [QUERY]: {query}")
        logger.info("🤖 [THINKING]: Checking if tools are needed...")
        
        response = self.llm.generate_with_tools(formatted_messages, tools=TOOLS)
        
        if "<tool_call>" in response or hasattr(self.llm.processor, 'decode_tool_calls'):
            logger.info("🎯 [DECISION]: LLM requested tool calls.")
            yield debug_json_list, "Đang sử dụng công cụ tra cứu chuyên sâu..."
            
            try:
                # Ánh xạ tên hàm sang thực thi thực tế
                available_tools = {
                    "extract_clause_point": extract_clause_point,
                    "extract_relevant_clause_point": extract_relevant_clause_point,
                    "extract_clause_point_references": extract_clause_point_references
                }

                # Parse tool call (Đoạn này hỗ trợ cả 3 hàm)
                import re
                tool_matches = re.findall(r'<tool_call>(.*?)</tool_call>', response, re.DOTALL)
                
                if not tool_matches:
                    match = re.search(r'\{.*\}', response, re.DOTALL)
                    if match:
                        tool_matches = [match.group()]

                tool_results_combined = []
                for tool_str in tool_matches:
                    try:
                        tool_data = json.loads(tool_str)
                        func_name = tool_data.get("name")
                        args = tool_data.get("arguments", {})

                        if func_name in available_tools:
                            logger.info(f"🚀 [FUNCTION CALL]: Calling {func_name} | Args: {args}")
                            results = available_tools[func_name](**args)
                            tool_result = format_records_for_llm(results)
                            tool_results_combined.append(tool_result)
                            logger.info(f"✅ [FUNCTION RESULT]: {func_name} returned {len(results)} records.")
                        else:
                            logger.warning(f"⚠️ [FUNCTION WARNING]: LLM tried to call unknown tool: {func_name}")
                    except Exception as e:
                        logger.error(f"❌ [PARSING ERROR]: Failed to parse tool data '{tool_str}': {e}")

                if tool_results_combined:
                    all_results_str = "\n\n".join(tool_results_combined)
                    
                    # Cập nhật ngữ cảnh và hỏi lại LLM
                    formatted_messages.append({"role": "assistant", "content": response})
                    formatted_messages.append({
                        "role": "user", 
                        "content": f"Kết quả từ các công cụ:\n{all_results_str}\n\nDựa trên thông tin bổ sung này, hãy trả lời câu hỏi của tôi một cách chi tiết và chính xác."
                    })
                    
                    # Sinh câu trả lời cuối cùng (stream)
                    full_response = ""
                    for chunk in self.llm.stream_generate(formatted_messages):
                        full_response += chunk
                        yield debug_json_list, full_response
                    return
                    
            except Exception as e:
                logger.error(f"💥 [CRITICAL ERROR]: Tool execution failed: {e}")

        # 4. Nếu không gọi tool hoặc tool lỗi, stream response bình thường
        logger.info("💬 [RESPONSE]: Generating final answer (No tools or Fallback).")
        full_response = ""
        for chunk in self.llm.stream_generate(formatted_messages):
            full_response += chunk
            yield debug_json_list, full_response

    def reset_history(self):
        pass
