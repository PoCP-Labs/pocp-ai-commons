"""Embedding similarity for skill/agent matching and semantic dedup (NN-2)."""

from __future__ import annotations

import math
import os

from services.ollama_client import ollama_embed_sync
from services.sentence_embedder import embed_text as st_embed_text, sentence_transformers_enabled


def ollama_embeddings_enabled() -> bool:
    return os.getenv("ENABLE_OLLAMA_EMBEDDINGS", "false").lower() == "true"


def embedding_provider() -> str | None:
    """Active embedding backend for this node, if any."""
    if sentence_transformers_enabled():
        return "sentence_transformers"
    if ollama_embeddings_enabled():
        return "ollama"
    return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


def embed_document(text: str) -> list[float] | None:
    """Embed text using the first available provider (ST preferred over Ollama)."""
    if sentence_transformers_enabled():
        vec = st_embed_text(text)
        if vec is not None:
            return vec
    if ollama_embeddings_enabled():
        return ollama_embed_sync(text)
    return None


def embedding_similarity(query: str, document: str) -> float | None:
    """Return cosine similarity in [0,1] or None if no embed backend available."""
    q = embed_document(query)
    d = embed_document(document)
    if q is None or d is None:
        return None
    return cosine_similarity(q, d)


def blend_keyword_and_embedding(keyword_score: float, query: str, document: str) -> float:
    """Blend keyword overlap with optional embedding similarity."""
    sim = embedding_similarity(query, document)
    if sim is None:
        return keyword_score
    weight = float(os.getenv("POCP_EMBED_MATCH_WEIGHT", os.getenv("OLLAMA_EMBED_MATCH_WEIGHT", "0.45")))
    weight = max(0.0, min(weight, 1.0))
    return round((1.0 - weight) * keyword_score + weight * sim, 4)
