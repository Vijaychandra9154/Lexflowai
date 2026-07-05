import os
from typing import List
from threading import Lock

from sentence_transformers import SentenceTransformer
import faiss
import openai

MODEL_NAME = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
embedder = SentenceTransformer(MODEL_NAME)


class LocalVectorIndex:
    def __init__(self):
        self.dim = embedder.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatL2(self.dim)
        self.texts: List[str] = []
        self._lock = Lock()

    def add(self, texts: List[str]):
        with self._lock:
            embs = embedder.encode(texts, show_progress_bar=False, convert_to_numpy=True)
            if len(embs.shape) == 1:
                embs = embs.reshape(1, -1)
            self.index.add(embs.astype("float32"))
            self.texts.extend(texts)

    def query(self, q: str, k: int = 5) -> List[str]:
        if not self.texts:
            return []
        q_emb = embedder.encode([q], convert_to_numpy=True).astype("float32")
        D, I = self.index.search(q_emb, k)
        results: List[str] = []
        for idx in I[0]:
            if idx < len(self.texts):
                results.append(self.texts[idx])
        return results


def llm_generate(prompt: str, max_tokens: int = 600, temperature: float = 0.2) -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY not set in environment")
    openai.api_key = key
    resp = openai.ChatCompletion.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": "You are a legal drafting assistant for Indian law."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp["choices"][0]["message"]["content"]


VECTOR_INDEX = LocalVectorIndex()
