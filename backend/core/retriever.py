import faiss
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path
import os

# Adjust path assuming this runs from backend/
INDEX_PATH = Path("vector_store/mental_health.index")
STORE_PATH = Path("vector_store/mental_health.json")

# 1. Disable parallelism/progress bars as per performance fix
os.environ["TOKENIZERS_PARALLELISM"] = "false"

class PDFRetriever:
    def __init__(self):
        self.index = None
        self.store = None
        self.model = None
        
        if INDEX_PATH.exists() and STORE_PATH.exists():
            print("Loading PDF Vector Store (Index only)...")
            self.index = faiss.read_index(str(INDEX_PATH))
            with open(STORE_PATH, "r") as f:
                self.store = json.load(f)
            # Model is now lazy loaded
        else:
            print(f"Warning: PDF Vector Store not found at {INDEX_PATH.absolute()}.")

    def _get_model(self):
        if self.model is None:
            print("Loading Retriever Model (Lazy, CPU)...")
            self.model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        return self.model

    def retrieve(self, query: str, top_k: int = 2): # Reduced top_k default
        if not self.index:
            return []

        model = self._get_model()
        # 3. Only embed user query, no progress bar
        q_emb = np.array(model.encode([query], show_progress_bar=False), dtype="float32")
        distances, indices = self.index.search(q_emb, top_k)

        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.store["texts"]):
                # Optional: Filter by distance if needed
                results.append(self.store["texts"][idx])

        return results

# Singleton instance
retriever = PDFRetriever()
