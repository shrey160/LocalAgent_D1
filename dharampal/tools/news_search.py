"""Historical news search tool.

Searches the local ChromaDB vector store for articles from a specific date.
If found, presents them and asks the user if they want to scrape SpaceNews
for more / fresher info.

Design notes (for reviewer):
- The tool does NOT perform web scraping itself — it only queries the RAG DB.
- Date extraction from natural language is handled by `dateparser`.
- The normalised date format ("Month DD, YYYY") is used for exact metadata
  matches in ChromaDB.
"""

from __future__ import annotations

import datetime
from typing import Any

import dateparser
from langchain_core.tools import tool

from dharampal.storage.chroma_store import ChromaNewsStore

_store = ChromaNewsStore()


def _extract_date(query: str) -> str | None:
    """Try to pull a calendar date out of free-form text.

    Returns a normalised string like "April 21, 2026" or None.
    """
    import re

    # Strip ordinal suffixes (st, nd, rd, th) so dateparser can handle them
    cleaned = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", query, flags=re.IGNORECASE)

    # Try to parse the whole string first
    settings = {
        "STRICT_PARSING": False,
        "PREFER_DATES_FROM": "past",
        "RETURN_AS_TIMEZONE_AWARE": False,
    }
    parsed = dateparser.parse(cleaned, settings=settings)
    if parsed:
        return parsed.strftime("%B %d, %Y")

    # Fallback: try to extract date-like tokens and parse subsets
    # Remove common noise words that confuse dateparser
    noise_words = {
        "news",
        "for",
        "get",
        "me",
        "show",
        "what",
        "happened",
        "on",
        "the",
        "about",
        "from",
        "some",
    }
    tokens = cleaned.split()
    filtered = [t for t in tokens if t.lower() not in noise_words]

    # Try progressively smaller suffixes from the right
    for i in range(len(filtered)):
        subset = " ".join(filtered[i:])
        parsed = dateparser.parse(subset, settings=settings)
        if parsed:
            return parsed.strftime("%B %d, %Y")

    return None


def _format_results(articles: list[dict[str, Any]], date_str: str) -> str:
    """Build a human-readable summary of the found articles."""
    if not articles:
        return (
            f"I don't have any space news cached for {date_str} yet.\n"
            f"Would you like me to check SpaceNews for articles from that date?"
        )

    lines = [f"Here are the space news articles I have cached for {date_str}:\n"]
    for i, art in enumerate(articles, 1):
        lines.append(f"{i}. {art['title']}")
        if art.get("excerpt"):
            lines.append(f"   {art['excerpt'][:200]}")
        if art.get("url"):
            lines.append(f"   {art['url']}")
        lines.append("")

    lines.append(
        "Would you like me to check SpaceNews online for more articles from that date?"
    )
    return "\n".join(lines)


@tool
def search_historical_news(query: str) -> str:
    """Search the local knowledge base for space news from a specific date.

    Use this when the user asks for news from a particular day, e.g.
    "What happened on April 21st?", "Show me news from last Tuesday",
    "Get me the headlines for March 15".

    The tool searches the local vector DB first. If articles are found it
    summarises them and asks whether to scrape SpaceNews for more.
    If nothing is found it asks the user for permission to scrape.

    Args:
        query: A natural-language phrase containing the target date.
    """
    date_str = _extract_date(query)
    if not date_str:
        return (
            "I'm not sure which date you're asking about. Could you rephrase with "
            "a specific date? For example: 'April 21, 2026' or 'yesterday'."
        )

    articles = _store.search_by_date(date_str)
    return _format_results(articles, date_str)
