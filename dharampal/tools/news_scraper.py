"""Historical news scraper tool.

Scrapes the SpaceNews archive for a *specific* date, stores the results in
ChromaDB, and returns them to the user.

Design notes (for reviewer):
- This is the "fallback" tool used after `search_historical_news` when the
  user says "yes" to checking SpaceNews online.
- It re-uses the same parsing/formatting logic as `space_news_tool` but
  accepts an arbitrary date instead of hard-coding "yesterday".
- Articles are automatically persisted to the vector store so future queries
  for the same date will hit the cache.
"""

from __future__ import annotations

import datetime
from typing import Any

import dateparser
from langchain_core.tools import tool

from dharampal.storage.chroma_store import ChromaNewsStore
from dharampal.tools.space_news import _parse_articles, _format_articles

_ARCHIVE_URL = "https://spacenews.com/section/news-archive/"
_store = ChromaNewsStore()


def _extract_date(query: str) -> datetime.date | None:
    """Pull a datetime.date out of free-form text."""
    import re

    # Strip ordinal suffixes (st, nd, rd, th) so dateparser can handle them
    cleaned = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", query, flags=re.IGNORECASE)

    settings = {
        "STRICT_PARSING": False,
        "PREFER_DATES_FROM": "past",
        "RETURN_AS_TIMEZONE_AWARE": False,
    }
    parsed = dateparser.parse(cleaned, settings=settings)
    if not parsed:
        return None
    return parsed.date()


def _fetch_and_scrape(target_date: datetime.date) -> list[dict[str, str]]:
    """Download the archive page and extract articles for *target_date*."""
    from dharampal.tools.space_news import _fetch_archive

    html = _fetch_archive()
    if html is None:
        return []

    return _parse_articles(html, target_date)


@tool
def scrape_historical_news(query: str) -> str:
    """Scrape SpaceNews for articles from a specific date and store them locally.

    Use this ONLY after the user has confirmed they want to check SpaceNews
    online (e.g. they replied "yes" to "Would you like me to check
    SpaceNews...?").

    Args:
        query: A natural-language phrase containing the target date.
    """
    target_date = _extract_date(query)
    if not target_date:
        return (
            "I couldn't determine which date to scrape. Please specify a clear date, "
            "for example 'April 21, 2026'."
        )

    articles = _fetch_and_scrape(target_date)
    if not articles:
        return (
            f"I couldn't find any SpaceNews articles for "
            f"{target_date.strftime('%B %d, %Y')}. "
            f"This could be because:\n"
            f"- The archive page is temporarily unavailable (rate limiting)\n"
            f"- The date is too far in the past\n"
            f"- The site structure has changed\n"
            f"Please try again in a few minutes."
        )

    # Persist to ChromaDB for future queries
    new_count = _store.add_articles(articles)

    result = _format_articles(articles, target_date)
    if new_count:
        result += f"\n\n(I've saved {new_count} new article(s) to my local memory.)"
    else:
        result += "\n\n(These articles were already in my local memory.)"

    return result
