import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict
from llm.chat_engine import ChatEngine
from dataclasses import asdict

app = FastAPI()

# Cấu hình CORS để Frontend có thể gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = ChatEngine()

class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]]

async def chat_generator(message: str, history: List[Dict[str, str]]):
    # engine.chat trả về generator: yield (docs, answer, thinking, tool_calls)
    for docs, answer, thinking, tool_calls in engine.chat(message, history):
        # CHÚ Ý: Phải convert dataclass sang dict ở đây
        docs_to_send = [asdict(d) if hasattr(d, '__dataclass_fields__') else d for d in docs]
        
        data = {
            "docs": docs_to_send,
            "answer": answer,
            "thinking": thinking,
            "tool_calls": tool_calls
        }
        # SSE format: "data: <json>\n\n"
        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.01)

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    return StreamingResponse(
        chat_generator(request.message, request.history),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)