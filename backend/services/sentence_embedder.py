"""Optional sentence-transformers embeddings (NN-2) — CPU-friendly semantic match & dedup."""

from __future__ import annotations

import os

_model = None


def sentence_transformers_enabled() -> bool:
    return os.getenv("ENABLE_SENTENCE_TRANSFORMERS", "false").lower() == "true"


def embedding_model_name() -> str:
    return os.getenv("POCP_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


def embed_text(text: str) -> list[float] | None:
    if not sentence_transformers_enabled() or not (text or "").strip():
        return None
    global _model
    try:
        if _model is None:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer(embedding_model_name())
        vector = _model.encode(text.strip(), normalize_embeddings=True)
        return vector.tolist()
    except Exception:
        return None
