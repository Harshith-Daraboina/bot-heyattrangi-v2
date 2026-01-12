from sentence_transformers import SentenceTransformer
from threading import Lock
import logging

logger = logging.getLogger(__name__)

class SharedResources:
    _instance = None
    _lock = Lock()
    
    def __init__(self):
        self._embedding_model = None
        self._model_lock = Lock()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = SharedResources()
        return cls._instance

    @property
    def embedding_model(self):
        """Lazy-loaded, thread-safe embedding model."""
        with self._model_lock:
            if self._embedding_model is None:
                logger.info("Initializing Shared Embedding Model (Lazy, CPU)...")
                # Using the exact same model definition as before
                self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
                logger.info("Shared Embedding Model Ready.")
        return self._embedding_model

# Global singleton access
shared = SharedResources.get_instance()
