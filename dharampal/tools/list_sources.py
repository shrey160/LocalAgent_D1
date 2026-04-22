"""List sources tool.

Shows the user which sources Dharampal can scrape from and which articles
are currently cached in the local RAG database.

Design notes (for reviewer):
- This is an informational tool — it doesn't scrape anything.
- It queries ChromaDB to show cached sources and article counts.
- It lists all available scrapers with their descriptions.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from langchain_core.tools import tool

from dharampal.storage.chroma_store import ChromaNewsStore

_store = ChromaNewsStore()

# Define available sources
SOURCES_INFO = {
    "SpaceNews": {
        "url": "https://spacenews.com/section/news-archive/",
        "description": "Space industry news and articles",
        "cached": True,  # Articles are stored in ChromaDB
    },
    "TradingEconomics": {
        "url": "https://tradingeconomics.com/",
        "description": "Financial markets and economic indicators",
        "cached": False,  # NOT stored in ChromaDB (ephemeral)
    },
}


def _get_cached_stats() -> dict[str, Any]:
    """Get statistics about cached articles from ChromaDB."""
    try:
        # Get all articles
        all_results = _store._collection.get()

        if not all_results or not all_results.get("ids"):
            return {"total": 0, "dates": [], "recent": []}

        total = len(all_results["ids"])

        # Extract unique dates from metadata
        dates = set()
        recent_articles = []

        metadatas = all_results.get("metadatas", [])
        for i, meta in enumerate(metadatas):
            if meta and "date" in meta:
                dates.add(meta["date"])

            # Get 5 most recent articles
            if i < 5 and meta:
                recent_articles.append(
                    {
                        "title": meta.get("title", "Unknown"),
                        "date": meta.get("date", "Unknown"),
                        "url": meta.get("url", ""),
                    }
                )

        return {
            "total": total,
            "dates": sorted(list(dates), reverse=True),
            "recent": recent_articles,
        }

    except Exception as e:
        return {"total": 0, "dates": [], "recent": [], "error": str(e)}


@tool
def list_sources_tool() -> str:
    """List all news sources and show which articles are cached locally.

    Use this when the user asks about sources, cached data, what's stored,
    or anything related to where the news comes from.

    Returns a summary of available scrapers and the current cache status.
    """
    lines = ["NEWS SOURCES\n"]

    # Available Sources
    lines.append("Available Sources:")
    lines.append("-" * 50)

    for name, info in SOURCES_INFO.items():
        lines.append(f"\n{name}:")
        lines.append(f"  URL: {info['url']}")
        lines.append(f"  Description: {info['description']}")
        lines.append(
            f"  Cached locally: {'[YES]' if info['cached'] else '[NO] (live only)'}"
        )

    # Cached Data Status
    lines.append("\n\nLocal Cache Status (RAG Database):")
    lines.append("-" * 50)

    stats = _get_cached_stats()

    if stats.get("error"):
        lines.append(f"Error reading cache: {stats['error']}")
    elif stats["total"] == 0:
        lines.append("No articles cached locally yet.")
        lines.append("Articles will be cached when you search for specific dates.")
    else:
        lines.append(f"Total cached articles: {stats['total']}")

        if stats["dates"]:
            lines.append(f"\nCached dates: {', '.join(stats['dates'][:10])}")
            if len(stats["dates"]) > 10:
                lines.append(f"  ... and {len(stats['dates']) - 10} more")

        if stats["recent"]:
            lines.append("\nMost recent cached articles:")
            for i, art in enumerate(stats["recent"], 1):
                lines.append(f"  {i}. {art['title']}")
                lines.append(f"     Date: {art['date']}")
                if art["url"]:
                    lines.append(f"     URL: {art['url']}")

    # Usage notes
    lines.append("\n\nUsage Notes:")
    lines.append("-" * 50)
    lines.append("- 'Daily news' -> SpaceNews (yesterday + day before)")
    lines.append("- 'Trading news' -> TradingEconomics (live, not cached)")
    lines.append("- 'News for [date]' -> Searches cache first, then scrapes if needed")
    lines.append("- Cached articles persist across sessions")

    return "\n".join(lines)
