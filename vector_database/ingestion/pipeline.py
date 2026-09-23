from ingestion.chunking.laws import chunk_laws
from vectorstore.bm25 import BM25
from vectorstore.upsert import upsert_chunks
from pathlib import Path
from vectorstore.qdrant import check_existed_collection

def ingestion_pipeline():
    if not check_existed_collection():
        chunks:list = chunk_laws()
        documents = [document['text'] for document in chunks]
        path = Path("./vectorstore/bm25store/bm25store.pkl")
        BM25(documents=documents).save_model(path)
        upsert_chunks(chunks)


if __name__ == "__main__":
    ingestion_pipeline()
        






