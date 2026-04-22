"""ChromaDB-backed vector store for space-news articles.

Design notes (for reviewer):
- Persistent ChromaDB client writes to `data/chroma_db/`.
- Each article is stored as a document with metadata (title, date, url, excerpt).
- The document ID is the article URL (natural unique key + dedup).
- Embeddings are generated via Ollama `nomic-embed-text:latest`.
- Two search modes:
    1. search_by_date() — exact date string match on metadata.
    2. search_by_query() — semantic similarity (optional, not used in v1).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

from dharampal.embeddings import get_embeddings

# Project root is two levels up from this file
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DB_PATH = _PROJECT_ROOT / "data" / "chroma_db"
_COLLECTION_NAME = "space_news"


def _ensure_db_dir() -> None:
    _DB_PATH.mkdir(parents=True, exist_ok=True)


class ChromaNewsStore:
    """Singleton-like persistent store for scraped space-news articles."""

    def __init__(self) -> None:
        _ensure_db_dir()
        self._client = chromadb.PersistentClient(
            path=str(_DB_PATH),
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def add_articles(self, articles: list[dict[str, str]]) -> int:
        """Embed and persist a list of article dicts.

        Each dict must have keys: title, date, url, excerpt.
        Returns the number of *new* articles added (duplicates skipped).
        """
        if not articles:
            return 0

        # Deduplicate by URL
        existing = self._collection.get()
        existing_ids = set(existing["ids"]) if existing and existing["ids"] else set()

        new_articles = [a for a in articles if a["url"] not in existing_ids]
        if not new_articles:
            return 0

        # Build payloads
        ids = [a["url"] for a in new_articles]
        documents = [self._article_to_text(a) for a in new_articles]
        metadatas = [
            {
                "title": a["title"],
                "date": self._normalise_date(a["date"]),
                "url": a["url"],
                "excerpt": a.get("excerpt", "")[:500],  # cap length
            }
            for a in new_articles
        ]

        # Generate embeddings via Ollama
        embeddings = get_embeddings(documents)

        self._collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        return len(new_articles)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def search_by_date(
        self, date_str: str, n_results: int = 20
    ) -> list[dict[str, Any]]:
        """Return articles whose metadata date matches *date_str* exactly.

        *date_str* should be in normalised form, e.g. "April 21, 2026".
        """
        results = self._collection.get(
            where={"date": date_str},
            limit=n_results,
        )
        return self._pack_results(results)

    def search_by_query(self, query: str, n_results: int = 5) -> list[dict[str, Any]]:
        """Semantic search over all stored articles."""
        from dharampal.embeddings import get_embedding

        query_embedding = get_embedding(query)
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
        )
        return self._pack_results(results)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _article_to_text(article: dict[str, str]) -> str:
        """Flatten an article dict into a single embeddable string."""
        parts = [article["title"], article.get("date", ""), article.get("excerpt", "")]
        return "\n".join(p for p in parts if p)

    @staticmethod
    def _normalise_date(raw_date: str) -> str:
        """Attempt to normalise a date string to 'Month DD, YYYY'.

        Falls back to the raw string if parsing fails.
        """
        import dateparser

        parsed = dateparser.parse(raw_date)
        if parsed:
            return parsed.strftime("%B %d, %Y")
        return raw_date.strip()

    @staticmethod
    def _pack_results(raw: dict[str, Any]) -> list[dict[str, Any]]:
        """Convert ChromaDB result dicts into plain article dicts."""
        out: list[dict[str, Any]] = []
        ids = raw.get("ids", [])
        documents = raw.get("documents", [])
        metadatas = raw.get("metadatas", [])
        distances = raw.get("distances", [])

        # Chroma returns nested lists for query(), flat lists for get()
        if ids and isinstance(ids[0], list):
            # query() shape: ids = [[id1, id2], ...]
            ids = ids[0] if ids else []
            documents = documents[0] if documents else []
            metadatas = metadatas[0] if metadatas else []
            distances = distances[0] if distances else []

        for i, doc_id in enumerate(ids):
            if doc_id is None:
                continue
            meta = metadatas[i] if i < len(metadatas) else {}
            out.append(
                {
                    "id": doc_id,
                    "document": documents[i] if i < len(documents) else "",
                    "title": meta.get("title", ""),
                    "date": meta.get("date", ""),
                    "url": meta.get("url", ""),
                    "excerpt": meta.get("excerpt", ""),
                    "distance": distances[i]
                    if distances and i < len(distances)
                    else None,
                }
            )
        return out
