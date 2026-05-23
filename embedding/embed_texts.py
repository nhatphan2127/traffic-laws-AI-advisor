from sentence_transformers import SentenceTransformer
from core.load_settings import load_settings
from core.setup_logging import setup_logging
import logging
from pyvi import ViTokenizer

settings = load_settings()
setup_logging()
logger = logging.getLogger('embedding')

_model = None
EMBEDDING_MODEL = settings['embedding']['model']
EMBEDDING_SIZE = settings['embedding']['batch_size']

def load_model():
    global _model
    if not _model:
        logger.info(f'Loadding embeding model. {EMBEDDING_MODEL}')
        _model = SentenceTransformer(EMBEDDING_MODEL)

    return _model


def embed_texts(texts:list)->list:
    model = load_model()

    segmented_texts = [ViTokenizer.tokenize(text) for text in texts]
    embeddings = model.encode(segmented_texts, batch_size=EMBEDDING_SIZE, normalize_embeddings=True, convert_to_tensor=False).tolist()
    # embeddings = model.encode(texts, batch_size=EMBEDDING_SIZE, normalize_embeddings=True, convert_to_tensor=False).tolist()
    logger.info(f'Completed embedding texts {len(texts)}')
    return embeddings
