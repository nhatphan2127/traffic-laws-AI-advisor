from ingestion.load_data import load_data
from ingestion.chunking.laws import chunk_laws
from vectorstore.bm25 import BM25
from vectorstore.upsert import upsert_chunks
from pathlib import Path

if __name__=='__main__':
    load_data()
    chunks = chunk_laws()
    upsert_chunks(chunks)

    documents = [document['text'] for document in chunks]
    path = Path("./vectorstore/bm25store/bm25store.pkl")
    BM25(documents=documents).save_model(path)




