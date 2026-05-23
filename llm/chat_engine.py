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
        Yields: (docs, answer, thinking, tool_calls)
        """
        # 1. RAG Retrieval ban đầu
        thinking_process = [f"Bắt đầu xử lý truy vấn: '{query}'"]
        yield [], "", thinking_process, []

        docs = retrieval(query)
        debug_json_list = [asdict(doc) for doc in docs]
        
        thinking_process.append(f"Tìm thấy {len(docs)} tài liệu thô từ cơ sở dữ liệu.")
        yield debug_json_list, "", thinking_process, []

        # 2. Xây dựng prompt cho LLM
        formatted_messages = [
            {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]}
        ]
        
        for msg in history:
            formatted_messages.append(msg)

        rag_prompt = get_rag_prompt(query, docs)
        formatted_messages.append({
            "role": "user", 
            "content": [{"type": "text", "text": rag_prompt}]
        })

        thinking_process.append("Đang gửi ngữ cảnh cho LLM để phân tích khả năng gọi hàm...")
        yield debug_json_list, "", thinking_process, []

        # 3. Vòng lặp kiểm tra Function Calling
        print(f"🔍 [QUERY]: {query}")
        
        response = self.llm.generate_with_tools(formatted_messages, tools=TOOLS)
        
        tool_calls_info = []
        if "<tool_call>" in response:
            logger.info("🎯 [DECISION]: LLM requested tool calls.")
            thinking_process.append(f"Model phản hồi: 'Cần sử dụng công cụ chuyên sâu để trả lời chính xác.'")
            
            try:
                available_tools = {
                    "extract_clause_point": extract_clause_point,
                    "extract_relevant_clause_point": extract_relevant_clause_point,
                    "extract_clause_point_references": extract_clause_point_references
                }

                import re
                tool_matches = re.findall(r'<tool_call>(.*?)</tool_call>', response, re.DOTALL)
                
                tool_results_combined = []
                for tool_str in tool_matches:
                    try:
                        tool_data = json.loads(tool_str)
                        func_name = tool_data.get("name")
                        args = tool_data.get("arguments", {})
                        
                        call_id = len(tool_calls_info) + 1
                        current_tool_call = {"id": call_id, "name": func_name, "args": args, "status": "running"}
                        tool_calls_info.append(current_tool_call)
                        
                        thinking_process.append(f"-> [Action {call_id}]: Gọi hàm '{func_name}' với tham số: {json.dumps(args, ensure_ascii=False)}")
                        yield debug_json_list, "", thinking_process, tool_calls_info

                        if func_name in available_tools:
                            results = available_tools[func_name](**args)
                            tool_result_str = format_records_for_llm(results)
                            tool_results_combined.append(tool_result_str)
                            
                            current_tool_call["status"] = "success"
                            current_tool_call["results_count"] = len(results)
                            # current_tool_call["raw_results"] = [asdict(r) for r in results] # Optional: too heavy?
                            
                            thinking_process.append(f"<- [Result {call_id}]: Hàm '{func_name}' trả về {len(results)} bản ghi chi tiết.")
                        else:
                            current_tool_call["status"] = "error"
                            current_tool_call["error"] = "Hàm không tồn tại"
                            thinking_process.append(f"<- [Result {call_id}]: Lỗi - Không tìm thấy hàm '{func_name}'.")
                        
                        yield debug_json_list, "", thinking_process, tool_calls_info
                    except Exception as e:
                        logger.error(f"❌ Tool parsing error: {e}")
                        thinking_process.append(f"!! [Error]: Lỗi khi xử lý lệnh gọi hàm: {str(e)}")

                if tool_results_combined:
                    thinking_process.append("Đang tổng hợp kết quả từ các công cụ vào ngữ cảnh cuối cùng...")
                    yield debug_json_list, "", thinking_process, tool_calls_info

                    all_results_str = "\n\n".join(tool_results_combined)
                    formatted_messages.append({"role": "assistant", "content": response})
                    formatted_messages.append({
                        "role": "user", 
                        "content": f"Kết quả từ các công cụ:\n{all_results_str}\n\nDựa trên thông tin bổ sung này, hãy trả lời câu hỏi của tôi một cách chi tiết và chính xác."
                    })
                    
                    full_response = ""
                    for chunk in self.llm.stream_generate(formatted_messages):
                        full_response += chunk
                        yield debug_json_list, full_response, thinking_process, tool_calls_info
                    return
                    
            except Exception as e:
                logger.error(f"💥 Tool execution failed: {e}")
                thinking_process.append(f"Lỗi khi gọi công cụ: {str(e)}")

        # 4. Nếu không gọi tool hoặc tool lỗi
        thinking_process.append("Đang tạo câu trả lời cuối cùng...")
        full_response = ""
        for chunk in self.llm.stream_generate(formatted_messages):
            full_response += chunk
            yield debug_json_list, full_response, thinking_process, tool_calls_info

    def reset_history(self):
        pass
