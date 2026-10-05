import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Service root (the folder containing config/, logs/, app/) so that paths do not
# depend on the current working directory.
BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"

LLM_PROVIDERS = ("google_studio", "cloud_ollama", "local_ollama")


@lru_cache
def load_settings() -> dict:
    load_dotenv(BASE_DIR / ".env")
    with open(CONFIG_DIR / "settings.yaml", "r", encoding="utf-8") as file:
        settings = yaml.safe_load(file)

    llm = settings.setdefault('llm', {})
    backend = settings.setdefault('backend', {})
    mcp = settings.setdefault('mcp', {})

    if os.getenv('GOOGLE_STUDIO_API_KEY'):
        llm['google_studio_api_key'] = os.getenv('GOOGLE_STUDIO_API_KEY')

    if os.getenv('GOOGLE_STUDIO_MODEL'):
        llm['google_studio_model'] = os.getenv('GOOGLE_STUDIO_MODEL')

    if os.getenv('CLOUD_OLLAMA_URL'):
        llm['cloud_ollama_url'] = os.getenv('CLOUD_OLLAMA_URL')

    if os.getenv('CLOUD_OLLAMA_KEY'):
        llm['cloud_ollama_key'] = os.getenv('CLOUD_OLLAMA_KEY')

    if os.getenv('CLOUD_OLLAMA_MODEL'):
        llm['cloud_ollama_model'] = os.getenv('CLOUD_OLLAMA_MODEL')

    if os.getenv('LOCAL_OLLAMA_URL'):
        llm['local_ollama_url'] = os.getenv('LOCAL_OLLAMA_URL')

    if os.getenv('LOCAL_OLLAMA_MODEL'):
        llm['local_ollama_model'] = os.getenv('LOCAL_OLLAMA_MODEL')

    if os.getenv('LOCAL_OLLAMA_KEY'):
        llm['local_ollama_key'] = os.getenv('LOCAL_OLLAMA_KEY')

    if os.getenv('LLM_TEMPERATURE'):
        llm['temperature'] = float(os.getenv('LLM_TEMPERATURE'))

    if os.getenv('LLM_MAX_TOKENS'):
        llm['max_tokens'] = int(os.getenv('LLM_MAX_TOKENS'))

    provider = (os.getenv('LLM_PROVIDER') or llm.get('provider') or '').strip()
    llm['provider'] = provider if provider in LLM_PROVIDERS else "google_studio"

    if os.getenv("MONGODB_URI"):
        backend['mongodb_uri'] = os.getenv("MONGODB_URI")

    if os.getenv("DB_NAME"):
        backend['db_name'] = os.getenv("DB_NAME")

    backend['jwt_secret'] = os.getenv("JWT_SECRET") or backend.get('jwt_secret') or "default_secret"
    backend['jwt_algorithm'] = os.getenv("JWT_ALGORITHM") or backend.get('jwt_algorithm') or "HS256"

    if os.getenv("RETRIEVAL_MCP_URL"):
        mcp['retrieval_server_url'] = os.getenv("RETRIEVAL_MCP_URL")
    mcp.setdefault('retrieval_server_url', "http://localhost:5555/mcp")

    if os.getenv("REQUEST_TIMEOUT"):
        mcp['request_timeout'] = int(os.getenv("REQUEST_TIMEOUT"))
    mcp['request_timeout'] = int(mcp.get('request_timeout') or 30)

    return settings
