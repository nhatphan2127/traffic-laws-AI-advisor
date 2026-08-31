import yaml
import os
from dotenv import load_dotenv


def load_settings():
    
    load_dotenv()
    with open('config/settings.yaml', 'r') as file:
        settings = yaml.safe_load(file)

    if os.getenv("JWT_SECRET", "default_secret"):
        settings['backend']['jwt_secret'] = os.getenv("JWT_SECRET", "default_secret")

    if os.getenv("JWT_ALGORITHM", "HS256"):
        settings['backend']['jwt_algorithm'] = os.getenv("JWT_ALGORITHM", "HS256")

    if os.getenv("MONGODB_URI"):
        settings['backend']['mongodb_uri'] = os.getenv("MONGODB_URI")

    if os.getenv("DB_NAME"):
        settings['backend']['db_name'] = os.getenv("DB_NAME")

    if os.getenv('EMBEDDING_MODEL'):
            settings['embedding']['model'] = os.getenv('EMBEDDING_MODEL')
    
    if os.getenv('EMBEDDING_MODEL'):
        settings['embedding']['batch_size'] = os.getenv('EMBEDDING_BATCH_SIZE', 16)

    if os.getenv('LLM_PROVIDER'):
        settings['llm']['provider'] = os.getenv('LLM_PROVIDER')

    if os.getenv('GOOGLE_STUDIO_API_KEY'):
        settings['llm']['google_studio_api_key'] = os.getenv('GOOGLE_STUDIO_API_KEY')

    if os.getenv('GOOGLE_STUDIO_MODEL'):
        settings['llm']['google_studio_model'] = os.getenv('GOOGLE_STUDIO_MODEL')

    if os.getenv('CLOUD_OLLAMA_URL'):
        settings['llm']['cloud_ollama_url'] = os.getenv('CLOUD_OLLAMA_URL')

    if os.getenv('CLOUD_OLLAMA_KEY'):
        settings['llm']['cloud_ollama_key'] = os.getenv('CLOUD_OLLAMA_KEY')

    if os.getenv('CLOUD_OLLAMA_MODEL'):
        settings['llm']['cloud_ollama_model'] = os.getenv('CLOUD_OLLAMA_MODEL')

    if os.getenv('LOCAL_OLLAMA_MODEL'):
        settings['llm']['local_ollama_model'] = os.getenv('LOCAL_OLLAMA_MODEL')
    
    if os.getenv('LOCAL_OLLAMA_KEY'):
        settings['llm']['local_ollama_key'] = os.getenv('LOCAL_OLLAMA_KEY')

    if os.getenv('LOCAL_OLLAMA_URL'):
        settings['llm']['local_ollama_url'] = os.getenv('LOCAL_OLLAMA_URL')
    
    if os.getenv('LLM_PROVIDER') in ['google_studio', 'cloud_ollama', 'local_ollama']:
        settings['llm']['provider'] = os.getenv('LLM_PROVIDER')
    else:
        settings['llm']['provider'] = "google_studio"

    if os.getenv('LLM_TEMPERATURE'):
        settings['llm']['temperature'] = float(os.getenv('LLM_TEMPERATURE', 0.1))

    if os.getenv('LLM_MAX_TOKENS'):
        settings['llm']['max_tokens'] = int(os.getenv('LLM_MAX_TOKENS', 1024))

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

    # Vector database overrides
    

    

    return settings
