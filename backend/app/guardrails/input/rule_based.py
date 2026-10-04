import re
import unicodedata
from typing import Dict, List, Optional

from guardrails.common import GuardrailResult


MAX_QUERY_LENGTH = 8000
MAX_HISTORY_MESSAGES = 50
MAX_HISTORY_CONTENT_LENGTH = 20000

_INJECTION_PATTERNS = (
    re.compile(r"\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?\b", re.IGNORECASE),
    re.compile(r"\b(disclose|reveal|print|show)\s+(?:the\s+)?(?:system|hidden)\s+prompt\b", re.IGNORECASE),
    re.compile(r"\b(?:bỏ qua|phớt lờ)\s+(?:(?:toàn bộ|mọi|tất cả)\s+)?(?:chỉ dẫn|hướng dẫn|quy tắc)\b", re.IGNORECASE),
    re.compile(r"\b(?:tiết lộ|in ra|hiển thị)\s+(?:toàn bộ\s+)?(?:system prompt|prompt hệ thống|chỉ dẫn ẩn)\b", re.IGNORECASE),
)


def _has_disallowed_control_characters(value: str) -> bool:
    return any(
        unicodedata.category(character) == "Cc" and character not in "\n\r\t"
        for character in value
    )


def check_input_rules(
    query: str, history: Optional[List[Dict[str, str]]] = None
) -> GuardrailResult:
    if not isinstance(query, str) or not query.strip():
        return GuardrailResult("block", "empty_query", "Vui lòng nhập câu hỏi.")
    if len(query) > MAX_QUERY_LENGTH:
        return GuardrailResult("block", "query_too_long", "Câu hỏi vượt quá giới hạn độ dài.")
    if _has_disallowed_control_characters(query):
        return GuardrailResult("block", "invalid_query_characters", "Câu hỏi chứa ký tự không hợp lệ.")

    if history is None:
        history = []
    if not isinstance(history, list) or len(history) > MAX_HISTORY_MESSAGES:
        return GuardrailResult("block", "invalid_history", "Lịch sử trò chuyện không hợp lệ.")

    texts_to_scan = [query]
    for message in history:
        if not isinstance(message, dict):
            return GuardrailResult("block", "invalid_history_message", "Lịch sử trò chuyện không hợp lệ.")

        role = message.get("role")
        content = message.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            return GuardrailResult("block", "invalid_history_message", "Lịch sử trò chuyện không hợp lệ.")
        if len(content) > MAX_HISTORY_CONTENT_LENGTH or _has_disallowed_control_characters(content):
            return GuardrailResult("block", "invalid_history_content", "Lịch sử trò chuyện không hợp lệ.")
        texts_to_scan.append(content)

    combined_text = "\n".join(texts_to_scan)
    if any(pattern.search(combined_text) for pattern in _INJECTION_PATTERNS):
        return GuardrailResult("review", "possible_prompt_injection")

    return GuardrailResult("allow")