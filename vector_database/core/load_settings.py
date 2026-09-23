import yaml
import os
from dotenv import load_dotenv


def load_settings():
    
    load_dotenv()
    with open('config/settings.yaml', 'r') as file:
        settings = yaml.safe_load(file)

    if os.getenv('EMBEDDING_MODEL'):
        settings['embedding']['model'] = os.getenv('EMBEDDING_MODEL')
    
    if os.getenv('EMBEDDING_MODEL'):
        settings['embedding']['batch_size'] = os.getenv('EMBEDDING_BATCH_SIZE', 16)

    if os.getenv('PROCESSED_DIR'):
        settings['data']['processed_dir'] = os.getenv('PROCESSED_DIR', "data/processed")

    if os.getenv('RAW_DIR'):
        settings['data']['raw_dir'] = os.getenv('RAW_DIR', "data/raw")

    if os.getenv('DB_TYPE'):
        settings['vector_database']['type'] = os.getenv('DB_TYPE', 'qdrant')
    
    if os.getenv('DB_HOST'):
        settings['vector_database']['host'] = os.getenv('DB_HOST', 'localhost')

    if os.getenv('DB_PORT'):
        settings['vector_database']['port'] = int(os.getenv('DB_PORT', 6333))

    if os.getenv('DB_URL'):
        settings['vector_database']['url'] = os.getenv('DB_URL', 'http://localhost:6333')

    if os.getenv('DB_API_KEY'):
        settings['vector_database']['api_key'] = os.getenv('DB_API_KEY', None)

    if os.getenv('DB_COLLECTION_NAME'):
        settings['vector_database']['collection_name'] = os.getenv('DB_COLLECTION_NAME', 'nmk_chatbot_collection')

    if os.getenv('DB_DISTANCE'):
        settings['vector_database']['distance'] = os.getenv('DB_DISTANCE', 'cosine')

    if os.getenv('DB_VECTOR_SIZE'):
        settings['vector_database']['vector_size'] = int(os.getenv('DB_VECTOR_SIZE', 1024))

    if os.getenv('DB_TIMEOUT'):
        settings['vector_database']['timeout'] = int(os.getenv('DB_TIMEOUT', 30))

    if os.getenv('TOP_K'):
        settings['retrieval']['top_k'] = int(os.getenv('TOP_K', 5))

    if os.getenv('DENSE_THRESHOLD'):
        settings['retrieval']['dense_threshold'] = float(os.getenv('DENSE_THRESHOLD', 0.4))

    if os.getenv('RRF_K'):
        settings['retrieval']['rrf_k'] = int(os.getenv('RRF_K', 60))

    if os.getenv('RR_ENABLED'):
        settings['retrieval']['reranker']['enabled'] = os.getenv('RR_ENABLED', 'False').lower() == 'true'
    
    if os.getenv('RR_MODEL'):
        settings['retrieval']['reranker']['model'] = os.getenv('RR_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')

    return settings
