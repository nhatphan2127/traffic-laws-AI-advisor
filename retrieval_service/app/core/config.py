import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Service root (the folder containing config/, data/, app/) so that paths do not
# depend on the current working directory.
BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"
# Generated artifacts (BM25 model, Qdrant snapshots) live outside the code package.
ARTIFACTS_DIR = BASE_DIR / "artifacts"
BM25_PATH = ARTIFACTS_DIR / "bm25store.pkl"


def resolve_path(path: str | Path) -> Path:
    """Resolve a (possibly relative) path against the service root."""
    path = Path(path)
    return path if path.is_absolute() else BASE_DIR / path


def _env_list(name: str) -> list[str] | None:
    value = os.getenv(name)
    if not value:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


@lru_cache
def load_settings() -> dict:
    load_dotenv(BASE_DIR / ".env")
    with open(CONFIG_DIR / "settings.yaml", "r", encoding="utf-8") as file:
        settings = yaml.safe_load(file)

    if os.getenv('EMBEDDING_MODEL'):
        settings['embedding']['model'] = os.getenv('EMBEDDING_MODEL')

    if os.getenv('EMBEDDING_BATCH_SIZE'):
        settings['embedding']['batch_size'] = int(os.getenv('EMBEDDING_BATCH_SIZE'))

    if os.getenv('PROCESSED_DIR'):
        settings['data']['processed_dir'] = os.getenv('PROCESSED_DIR')

    if os.getenv('RAW_DIR'):
        settings['data']['raw_dir'] = os.getenv('RAW_DIR')

    if os.getenv('DB_TYPE'):
        settings['vector_database']['type'] = os.getenv('DB_TYPE')

    if os.getenv('DB_HOST'):
        settings['vector_database']['host'] = os.getenv('DB_HOST')

    if os.getenv('DB_PORT'):
        settings['vector_database']['port'] = int(os.getenv('DB_PORT'))

    if os.getenv('DB_URL'):
        settings['vector_database']['url'] = os.getenv('DB_URL')

    if os.getenv('DB_API_KEY'):
        settings['vector_database']['api_key'] = os.getenv('DB_API_KEY')

    if os.getenv('DB_COLLECTION_NAME'):
        settings['vector_database']['collection_name'] = os.getenv('DB_COLLECTION_NAME')

    if os.getenv('DB_DISTANCE'):
        settings['vector_database']['distance'] = os.getenv('DB_DISTANCE')

    if os.getenv('DB_VECTOR_SIZE'):
        settings['vector_database']['vector_size'] = int(os.getenv('DB_VECTOR_SIZE'))

    if os.getenv('DB_TIMEOUT'):
        settings['vector_database']['timeout'] = int(os.getenv('DB_TIMEOUT'))

    if os.getenv('TOP_K'):
        settings['retrieval']['top_k'] = int(os.getenv('TOP_K'))

    if os.getenv('DENSE_THRESHOLD'):
        settings['retrieval']['dense_threshold'] = float(os.getenv('DENSE_THRESHOLD'))

    if os.getenv('RRF_K'):
        settings['retrieval']['rrf_k'] = int(os.getenv('RRF_K'))

    if os.getenv('RR_ENABLED'):
        settings['retrieval']['reranker']['enabled'] = os.getenv('RR_ENABLED').lower() == 'true'

    if os.getenv('RR_MODEL'):
        settings['retrieval']['reranker']['model'] = os.getenv('RR_MODEL')

    mcp_settings = settings.setdefault('mcp', {})
    if _env_list('MCP_ALLOWED_HOSTS'):
        mcp_settings['allowed_hosts'] = _env_list('MCP_ALLOWED_HOSTS')
    if _env_list('MCP_ALLOWED_ORIGINS'):
        mcp_settings['allowed_origins'] = _env_list('MCP_ALLOWED_ORIGINS')

    return settings
