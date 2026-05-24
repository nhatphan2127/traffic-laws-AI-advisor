from ingestion.load_data import load_data
from ingestion.chunking.laws import chunk_laws
from vectorstore.bm25 import BM25
from vectorstore.upsert import upsert_chunks
from pathlib import Path
from utils.histogram import visualize_chunk_distribution
if __name__=='__main__':
    # load_data()
    chunks:list = chunk_laws()
    # print(chunks[20:25])
    visualize_chunk_distribution([{"text" : chunk["text"]} for chunk in chunks])
    
    documents = [document['text'] for document in chunks]
    path = Path("./vectorstore/bm25store/bm25store.pkl")
    BM25(documents=documents).save_model(path)

    upsert_chunks(chunks)






