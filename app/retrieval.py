"""Evidence retrieval via FAISS."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

import faiss
from app.config import get_settings
from models.embedder import embed_text


class RetrievalError(RuntimeError):
    """Custom error raised when retrieval resources are missing."""


class EvidenceRetriever:
    """Retrieve top-k evidence chunks for a claim."""

    def __init__(self, index_path: Path, metadata_path: Path) -> None:
        if not index_path.exists() or not metadata_path.exists():
            raise RetrievalError(
                "Vector index or metadata not found. Run scripts/data_process.py first."
            )
        self.index = faiss.read_index(str(index_path))
        self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    def retrieve(self, query: str, top_k: int = 5) -> List[dict]:
        query_emb = embed_text(query, normalize=True).reshape(1, -1)
        distances, indices = self.index.search(query_emb.astype("float32"), top_k)
        results: List[dict] = []
        for idx, score in zip(indices[0], distances[0]):
            if idx == -1:
                continue
            meta = self.metadata[idx]
            results.append(
                {
                    "text": meta["text"],
                    "source": meta.get("source", "unknown"),
                    "chunk_index": meta.get("chunk_index"),
                    "score": float(score),
                }
            )
        return results


_retriever: EvidenceRetriever | None = None


def get_retriever() -> EvidenceRetriever:
    global _retriever
    if _retriever is None:
        settings = get_settings()
        _retriever = EvidenceRetriever(settings.index_path, settings.metadata_path)
    return _retriever
