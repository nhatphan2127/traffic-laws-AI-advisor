import yaml
import os
from dotenv import load_dotenv


def load_settings():
    
    load_dotenv()
    with open('config/settings.yaml', 'r') as file:
        settings = yaml.safe_load(file)

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

    if os.getenv('LOCAL_OLLAMA_URL'):
        settings['llm']['local_ollama_url'] = os.getenv('LOCAL_OLLAMA_URL')
    
    if os.getenv('LOCAL_OLLAMA_MODEL'):
        settings['llm']['local_ollama_model'] = os.getenv('LOCAL_OLLAMA_MODEL')
    
    if os.getenv('LOCAL_OLLAMA_KEY'):
        settings['llm']['local_ollama_key'] = os.getenv('LOCAL_OLLAMA_KEY')

    if os.getenv('LLM_TEMPERATURE'):
        settings['llm']['temperature'] = float(os.getenv('LLM_TEMPERATURE', 0.1))

    if os.getenv('LLM_MAX_TOKENS'):
        settings['llm']['max_tokens'] = int(os.getenv('LLM_MAX_TOKENS', 1024))

    if os.getenv('LLM_PROVIDER') in ['google_studio', 'cloud_ollama', 'local_ollama']:
        settings['llm']['provider'] = os.getenv('LLM_PROVIDER')
    else:
        settings['llm']['provider'] = "google_studio"

    if os.getenv("MONGODB_URI"):
        settings['backend']['mongodb_uri'] = os.getenv("MONGODB_URI")
    
    if os.getenv("DB_NAME"):
        settings['backend']['db_name'] = os.getenv("DB_NAME")

    if os.getenv("JWT_SECRET", "default_secret"):
        settings['backend']['jwt_secret'] = os.getenv("JWT_SECRET", "default_secret")

    if os.getenv("JWT_ALGORITHM", "HS256"):
        settings['backend']['jwt_algorithm'] = os.getenv("JWT_ALGORITHM", "HS256")

    if os.getenv("VECTOR_DATABASE_API_URL", "http://localhost:5555/api"):
        settings['api']['vector_database_api_url'] = os.getenv("VECTOR_DATABASE_API_URL", "http://localhost:5555/api")

    if os.getenv("REQUEST_TIMEOUT", 30):
        settings['api']['request_timeout'] = int(os.getenv("REQUEST_TIMEOUT", 30))

    
    return settings
