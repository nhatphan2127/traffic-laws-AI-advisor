import logging
import math
import re
import pickle
from collections import Counter
from pyvi import ViTokenizer

logger = logging.getLogger('sparse_vector')

class BM25:
    def __init__(self, documents: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_count = len(documents)
        
        # Global stats needed for BM25
        self.idf = {}
        self.avgdl = 0
        
        self._build_corpus_stats(documents)

    def _tokenize(self, text: str) -> list[str]:
        """Cleans and splits text into a list of words."""
        segmented_text = ViTokenizer.tokenize(text)
        # Lowercase and remove anything that isn't a word or space
        lowered_text = segmented_text.lower()
        clean_text = re.sub(r"[^\w\s]", '', lowered_text)
        return clean_text.split()

    def _build_corpus_stats(self, documents: list[str]):
        """Calculates IDF and Average Document Length from the initial corpus."""
        total_length = 0
        df = {}  # Document Frequency

        for doc in documents:
            tokens = self._tokenize(doc)
            total_length += len(tokens)
            
            # Count unique terms in this document for DF
            unique_terms = set(tokens)
            for term in unique_terms:
                df[term] = df.get(term, 0) + 1
        
        # Calculate Average Document Length
        self.avgdl = total_length / self.doc_count if self.doc_count > 0 else 0
        
        # Calculate IDF for every term found in the corpus
        for term, count in df.items():
            # Standard BM25 IDF formula
            self.idf[term] = math.log(
                (self.doc_count - count + 0.5) / (count + 0.5) + 1
            )
        
        # Create a vocabulary mapping for sparse vectors
        self.vocab = {term: i for i, term in enumerate(sorted(self.idf.keys()))}
        
        logger.info(f"Initialized BM25: {self.doc_count} docs, {len(self.idf)} terms.")

    def get_sparse_vector(self, text: str) -> dict:
        """
        Converts text into a Qdrant-compatible sparse vector:
        { "indices": [int, ...], "values": [float, ...] }
        """
        tokens = self._tokenize(text)
        doc_term_freqs = Counter(tokens)
        doc_len = len(tokens)
        
        indices = []
        values = []
        
        for term, tf in doc_term_freqs.items():
            if term in self.vocab:
                idx = self.vocab[term]
                idf = self.idf[term]
                
                # BM25-based weighting for the sparse vector values
                # score = idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * (doc_len / avgdl)))
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avgdl))
                weight = idf * (numerator / denominator)
                
                indices.append(idx)
                values.append(float(weight))
        
        # Qdrant expects sorted indices for sparse vectors
        if indices:
            sorted_pairs = sorted(zip(indices, values))
            indices, values = zip(*sorted_pairs)
            
        return {
            "indices": list(indices),
            "values": list(values)
        }

    def score(self, query: str, doc: str) -> float:
        """
        Calculates the BM25 score for a specific query string 
        against a specific document string.
        """
        query_tokens = self._tokenize(query)
        doc_tokens = self._tokenize(doc)
        
        # Create a dictionary of term frequencies for THIS specific document
        doc_term_freqs = Counter(doc_tokens)
        doc_len = len(doc_tokens)
        
        score = 0.0
        for token in query_tokens:
            # If the word was never in the original corpus, it has no IDF weight
            if token not in self.idf:
                continue
            
            # f(qi, D) -> how many times query term appears in this doc
            f_qi_D = doc_term_freqs.get(token, 0)
            idf = self.idf[token]
            
            # BM25 Formula components
            numerator = f_qi_D * (self.k1 + 1)
            denominator = f_qi_D + self.k1 * (1 - self.b + self.b * (doc_len / self.avgdl))
            
            score += idf * (numerator / denominator)
            
        return score
    def save_model(self, filepath: str):
        """Saves the current BM25 state to a file."""
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(self, f)
            logger.info(f"Model saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")

    @staticmethod
    def load_model(filepath: str):
        """Loads a BM25 state from a file and returns an instance."""
        try:
            with open(filepath, 'rb') as f:
                model = pickle.load(f)
            logger.info(f"Model loaded from {filepath}")
            return model
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return None