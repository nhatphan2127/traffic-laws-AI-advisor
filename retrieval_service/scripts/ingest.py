"""Chunk the processed legal documents, build the BM25 model and upsert into Qdrant.

    python scripts/ingest.py        (from the retrieval_service folder)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.logging_setup import setup_logging  # noqa: E402
from app.ingestion.pipeline import ingestion_pipeline  # noqa: E402

if __name__ == "__main__":
    setup_logging()
    ingestion_pipeline()
