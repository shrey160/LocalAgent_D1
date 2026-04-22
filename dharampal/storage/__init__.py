"""Storage package for Dharampal.

Provides a ChromaDB-based vector store for article metadata.
"""

from dharampal.storage.chroma_store import ChromaNewsStore

__all__ = ["ChromaNewsStore"]
