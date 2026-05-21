import yaml
import os
from dotenv import load_dotenv


def load_settings():
    load_dotenv()
    with open('config/settings.yaml', 'r') as file:
        settings = yaml.safe_load(file)

    if os.getenv('UNSTRUCTURED_API_KEY'):
        settings['api_key']['unstructured_api_key'] = os.getenv('UNSTRUCTURED_API_KEY')
    if os.getenv('LLAMAINDEX_API'):
        settings['api_key']['llamaindex_api'] = os.getenv('LLAMAINDEX_API')

    if os.getenv('EMBEDDING_MODEL'):
        settings['embedding']['model'] = os.getenv('EMBEDDING_MODEL')

    if os.getenv('EMBEDDING_MODEL'):
        settings['embedding']['batch_size'] = os.getenv('EMBEDDING_BATCH_SIZE', 16)

    if os.getenv('CHUNKING_SIZE'):
        settings['chunking']['size'] = os.getenv('CHUNKING_SIZE', 512)

    # Vector database overrides
    if os.getenv("QDRANT_URL"):
        settings["vector_database"]["url"] = os.getenv("QDRANT_URL")
    if os.getenv("QDRANT_API_KEY"):
        settings["vector_database"]["api_key"] = os.getenv("QDRANT_API_KEY")
    if os.getenv("QDRANT_COLLECTION_NAME"):
        settings["vector_database"]["collection_name"] = os.getenv("QDRANT_COLLECTION_NAME")
    if os.getenv("QDRANT_TIMEOUT"):
        settings["vector_database"]["timeout"] = int(os.getenv("QDRANT_TIMEOUT"))

    return settings
