"""Embedding and similarity service.

Supports multiple backends:
- **Ollama** embeddings (local, free)
- **OpenAI** embeddings (API-based)
- **TF-IDF** fallback (no external service needed)
"""

import re
import math
import logging
from typing import Optional
from collections import Counter

from recruiter_workflow.config import settings

logger = logging.getLogger(__name__)


# ─── TF-IDF based similarity (zero dependencies) ─────────────────────────────

def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer."""
    return re.findall(r'\b[a-z0-9]+\b', text.lower())


def _tf(tokens: list[str]) -> dict[str, float]:
    """Term frequency (normalized)."""
    counts = Counter(tokens)
    total = len(tokens) or 1
    return {t: c / total for t, c in counts.items()}


def _cosine_sim(v1: dict[str, float], v2: dict[str, float]) -> float:
    """Cosine similarity between two sparse vectors."""
    all_keys = set(v1) | set(v2)
    dot = sum(v1.get(k, 0) * v2.get(k, 0) for k in all_keys)
    mag1 = math.sqrt(sum(v ** 2 for v in v1.values())) or 1e-10
    mag2 = math.sqrt(sum(v ** 2 for v in v2.values())) or 1e-10
    return dot / (mag1 * mag2)


def compute_similarity_tfidf(text1: str, text2: str) -> float:
    """Compute similarity using TF-IDF cosine similarity. No external deps needed."""
    tf1 = _tf(_tokenize(text1))
    tf2 = _tf(_tokenize(text2))
    return round(_cosine_sim(tf1, tf2), 4)


# ─── Ollama embeddings ───────────────────────────────────────────────────────

def compute_similarity_ollama(text1: str, text2: str) -> float:
    """Compute similarity using Ollama embeddings."""
    if settings.OLLAMA_MODEL not in ["nomic-embed-text", "mxbai-embed-large", "all-minilm"]:
        return compute_similarity_tfidf(text1, text2)
        
    try:
        import ollama
        client = ollama.Client(host=settings.OLLAMA_BASE_URL)
        
        emb1 = client.embed(model=settings.OLLAMA_MODEL, input=text1)["embeddings"][0]
        emb2 = client.embed(model=settings.OLLAMA_MODEL, input=text2)["embeddings"][0]
        
        # Cosine similarity
        import numpy as np
        v1 = np.array(emb1)
        v2 = np.array(emb2)
        sim = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-10))
        return round(max(0.0, sim), 4)
    except Exception as e:
        logger.warning(f"Ollama embedding failed, falling back to TF-IDF: {e}")
        return compute_similarity_tfidf(text1, text2)


# ─── OpenAI embeddings ──────────────────────────────────────────────────────

def compute_similarity_openai(text1: str, text2: str) -> float:
    """Compute similarity using OpenAI embeddings."""
    try:
        import openai
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        resp = client.embeddings.create(
            model="text-embedding-3-small",
            input=[text1[:8000], text2[:8000]],
        )
        
        import numpy as np
        v1 = np.array(resp.data[0].embedding)
        v2 = np.array(resp.data[1].embedding)
        sim = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-10))
        return round(max(0.0, sim), 4)
    except Exception as e:
        logger.warning(f"OpenAI embedding failed, falling back to TF-IDF: {e}")
        return compute_similarity_tfidf(text1, text2)


# ─── Main dispatch ───────────────────────────────────────────────────────────

def compute_similarity(text1: str, text2: str) -> float:
    """Compute similarity between two texts using the configured provider.
    
    Falls back gracefully: Cloud OpenAI / Ollama → local TF-IDF matcher.
    """
    provider = settings.LLM_PROVIDER.lower()
    
    try:
        if provider == "ollama":
            return compute_similarity_ollama(text1, text2)
        elif provider == "openai" and settings.OPENAI_API_KEY:
            return compute_similarity_openai(text1, text2)
        else:
            return compute_similarity_tfidf(text1, text2)
    except Exception as e:
        logger.warning(f"Cloud/Provider embedding error ({e}), engaging local TF-IDF fallback.")
        return compute_similarity_tfidf(text1, text2)
