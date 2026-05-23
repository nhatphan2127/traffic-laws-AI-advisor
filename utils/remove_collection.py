from qdrant_client import QdrantClient

collection_name = "nmk_chatbot_collection"

client = QdrantClient(url="http://localhost:6333/", api_key=None)

client.delete_collection(
    collection_name=collection_name
)
