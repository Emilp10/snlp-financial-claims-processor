"""Utilities for loading a sentence-transformer embedder."""
from functools import lru_cache
from typing import Iterable, List

import numpy as np
from sentence_transformers import SentenceTransformer


def _get_model_name() -> str:
    """Return the embedding model name, defaulting to a lightweight local model."""
    from os import getenv

    return getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")


@lru_cache(maxsize=1)
def _load_model() -> SentenceTransformer:
    """Load and cache the embedding model to avoid repeated downloads."""
    model_name = _get_model_name()
    return SentenceTransformer(model_name)


def embed_texts(texts: Iterable[str], normalize: bool = True) -> np.ndarray:
    """Return embeddings for the provided texts."""
    model = _load_model()
    embeddings = model.encode(list(texts), normalize_embeddings=normalize)
    return np.asarray(embeddings, dtype="float32")


def embed_text(text: str, normalize: bool = True) -> np.ndarray:
    """Return a single embedding for convenience."""
    return embed_texts([text], normalize=normalize)[0]
