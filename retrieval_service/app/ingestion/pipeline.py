from app.core.config import BM25_PATH
from app.core.logging_setup import setup_logging
from app.ingestion.chunking.laws import chunk_laws
from app.vectorstore.bm25 import BM25
from app.vectorstore.upsert import upsert_chunks
from app.vectorstore.qdrant import check_existed_collection

def ingestion_pipeline():
    if not check_existed_collection():
        chunks:list = chunk_laws()
        documents = [document['text'] for document in chunks]
        BM25_PATH.parent.mkdir(parents=True, exist_ok=True)
        BM25(documents=documents).save_model(BM25_PATH)
        upsert_chunks(chunks)


if __name__ == "__main__":
    # Prefer: python scripts/ingest.py
    setup_logging()
    ingestion_pipeline()
        






