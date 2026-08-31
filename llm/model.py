import json
import logging
from typing import Dict, Generator, List, Optional, Tuple
import requests
from ollama import Client

from core.load_settings import load_settings
from core.setup_logging import setup_logging

class LLMModel:
    def __init__(self):
        # 1. Initialize logging
        setup_logging()
        self.logger = logging.getLogger("llm")

        settings = load_settings()
        llm_settings = settings.get("llm", {})

        # 2. Reuse HTTP Session for better performance
        self.session = requests.Session()

        # 3. Google AI Studio Configuration
        self.google_api_key = llm_settings.get("google_studio_api_key", "")
        self.google_model = llm_settings.get("google_studio_model", "")

        # 4. Cloud Ollama Configuration
        self.cloud_ollama_url = llm_settings.get("cloud_ollama_url", "")
        self.cloud_ollama_key = llm_settings.get("cloud_ollama_key", "")
        self.cloud_ollama_model = llm_settings.get("cloud_ollama_model", "")

        # Initialize Client for Cloud Ollama
        self._cloud_ollama_client: Optional[Client] = None
        if self.cloud_ollama_url:
            headers = {}
            if self.cloud_ollama_key:
                headers["Authorization"] = f"Bearer {self.cloud_ollama_key}"
            self._cloud_ollama_client = Client(host=self.cloud_ollama_url, headers=headers)

        # 5. Local Ollama Configuration
        self.api_url = llm_settings.get("local_ollama_url", "http://localhost:11434/api/chat")
        self.api_key = llm_settings.get("local_ollama_key", "")
        self.model = llm_settings.get("local_ollama_model", "llama3.2")

        # 6. Hyperparameters & Provider
        self.temperature = llm_settings.get("temperature", 0.7)
        self.max_new_tokens = llm_settings.get("max_tokens", 2048)
        self.provider = llm_settings.get("provider", "ollama_local")

        # Logging thông tin khởi tạo
        self.logger.info(f"Initialized LLMModel with default provider: '{self.provider}'")
        self._log_provider_info(self.provider)

    def _log_provider_info(self, provider: str):
        """Support logging with detailed information about the active LLM provider."""
        if provider in ["google", "google_studio"]:
            self.logger.info(f"Active LLM Provider: Google AI Studio ({self.google_model})")
        elif provider == "cloud_ollama":
            self.logger.info(f"Active LLM Provider: Cloud Ollama ({self.cloud_ollama_model}) at {self.cloud_ollama_url}")
        else:
            self.logger.info(f"Active LLM Provider: Local Ollama ({self.model}) at {self.api_url}")

    def _to_gemini_payload(self, messages: List[Dict[str, str]]) -> Dict:
        """Convert a list of messages to the payload format for the Gemini API."""
        contents = []
        system_instruction = None

        for m in messages:
            role = m.get("role")
            content = m.get("content", "")

            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            elif role == "user":
                contents.append({"role": "user", "parts": [{"text": content}]})
            elif role in ["assistant", "model"]:
                contents.append({"role": "model", "parts": [{"text": content}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_new_tokens,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        return payload

    def _call_gemini(self, messages: List[Dict[str, str]]) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.google_model}:generateContent?key={self.google_api_key}"
        payload = self._to_gemini_payload(messages)
        
        self.logger.debug(f"Calling Gemini API model: '{self.google_model}'")
        try:
            response = self.session.post(url, json=payload, timeout=60)
            response.raise_for_status()
            res_json = response.json()
            
            candidates = res_json.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
            return ""
        except Exception as e:
            self.logger.error(f"Error calling Gemini API: {e}", exc_info=True)
            return f"Error: Unable to call Gemini. {str(e)}"

    def _stream_gemini(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.google_model}:streamGenerateContent?key={self.google_api_key}"
        payload = self._to_gemini_payload(messages)

        self.logger.debug(f"Streaming from Gemini API model: '{self.google_model}'")
        try:
            response = self.session.post(url, json=payload, stream=True, timeout=60)
            response.raise_for_status()

            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                
                # Clean the line received from the Gemini SSE Stream
                cleaned = line.strip()
                if cleaned.startswith("data:"):
                    cleaned = cleaned[5:].strip()
                if cleaned.startswith("[") or cleaned.startswith(","):
                    cleaned = cleaned[1:].strip()
                if cleaned.endswith("]"):
                    cleaned = cleaned[:-1].strip()

                if not cleaned:
                    continue

                try:
                    data = json.loads(cleaned)
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            text_chunk = parts[0].get("text", "")
                            if text_chunk:
                                yield text_chunk
                except json.JSONDecodeError:
                    continue

        except Exception as e:
            self.logger.error(f"Error streaming from Gemini API: {e}", exc_info=True)
            yield f"\n[Streaming Error: {str(e)}]"

    def _call_cloud_ollama(self, messages: List[Dict[str, str]], stream: bool = True):
        if not self._cloud_ollama_client:
            headers = {}
            if self.cloud_ollama_key:
                headers["Authorization"] = f"Bearer {self.cloud_ollama_key}"
            self._cloud_ollama_client = Client(host=self.cloud_ollama_url, headers=headers)

        self.logger.debug(f"Calling Cloud Ollama ('{self.cloud_ollama_model}', stream={stream})")
        try:
            response = self._cloud_ollama_client.chat(
                model=self.cloud_ollama_model,
                messages=messages,
                stream=stream
            )

            if stream:
                return self._stream_cloud_ollama(response)

            thinking = getattr(response.message, 'thinking', '') or ''
            content = getattr(response.message, 'content', '') or ''
            return thinking, content

        except Exception as e:
            self.logger.error(f"Error calling Cloud Ollama ({self.cloud_ollama_url}): {e}", exc_info=True)
            raise

    def _stream_cloud_ollama(self, response) -> Generator[Tuple[bool, str], None, None]:
        in_thinking = False

        for chunk in response:
            msg = getattr(chunk, "message", None)
            if not msg:
                continue

            thinking = getattr(msg, "thinking", None)
            content = getattr(msg, "content", None)

            if thinking:
                in_thinking = True
                yield in_thinking, thinking
            elif content:
                in_thinking = False
                yield in_thinking, content

    def _call_ollama(self, messages: List[Dict[str, str]], stream: bool = False):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_new_tokens
            }
        }

        self.logger.debug(f"Calling Local Ollama API ('{self.model}' at {self.api_url})")
        try:
            response = self.session.post(self.api_url, headers=headers, json=payload, stream=stream, timeout=60)
            response.raise_for_status()

            if stream:
                return response
            
            result_json = response.json()
            return result_json.get("message", {}).get("content", "")

        except Exception as e:
            self.logger.error(f"Error calling Local Ollama ({self.api_url}): {e}", exc_info=True)
            if stream:
                raise e
            return f"Error: Unable to call Ollama. {str(e)}"

    def _stream_ollama(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        try:
            response = self._call_ollama(messages, stream=True)
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    try:
                        data = json.loads(line)
                        text_chunk = data.get("message", {}).get("content", "")
                        if text_chunk:
                            yield text_chunk
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            self.logger.error(f"Error streaming from Local Ollama: {e}", exc_info=True)
            yield f"\n[Streaming Error: {str(e)}]"

    def generate(self, messages: List[Dict[str, str]], stream: bool = True):
        """Routing the call to the appropriate LLM provider based on the specified or default provider."""
        
        if self.provider == "google_studio":
            return self._call_gemini(messages)
        elif self.provider == "local_ollama":
            return self._call_ollama(messages, stream=stream)
        else:
            return self._call_cloud_ollama(messages, stream=stream)

    def stream_generate(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        """Routing the stream call for text response."""

        if self.provider == "google_studio":
            yield from self._stream_gemini(messages)
        elif self.provider == "local_ollama":
            yield from self._stream_ollama(messages)
        else:
            for _, content in self._call_cloud_ollama(messages, stream=True):
                yield content