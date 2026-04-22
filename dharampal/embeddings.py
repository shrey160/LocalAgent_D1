"""Ollama embedding client.

Connects to the local Ollama server (default port 11434) and generates
dense vector embeddings using `nomic-embed-text:latest`.

Design notes (for reviewer):
- We use the raw Ollama HTTP API rather than the official Python client so
  we avoid an extra dependency.
- The model must already be pulled (`ollama pull nomic-embed-text`).
- Embeddings are cached in-memory for the lifetime of the process.
"""

from __future__ import annotations

import requests
from typing import Any

OLLAMA_URL = "http://localhost:11434/api/embeddings"
MODEL_NAME = "nomic-embed-text:latest"

# Simple process-level cache: text -> vector
_EMBED_CACHE: dict[str, list[float]] = {}


def get_embedding(text: str) -> list[float]:
    """Return the embedding vector for *text* using Ollama.

    Raises RuntimeError if Ollama is not reachable or returns an error.
    """
    if text in _EMBED_CACHE:
        return _EMBED_CACHE[text]

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": MODEL_NAME, "prompt": text},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        vector = data["embedding"]
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Could not reach Ollama at {OLLAMA_URL}. Is it running?"
        ) from exc
    except KeyError as exc:
        raise RuntimeError(f"Unexpected response from Ollama: {data}") from exc

    _EMBED_CACHE[text] = vector
    return vector


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Batch embedding. Falls back to sequential calls."""
    return [get_embedding(t) for t in texts]
