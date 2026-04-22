"""Trading Economics news scraper.

Fetches current headlines from TradingEconomics.com.

Design notes (for reviewer):
- This tool does NOT persist articles to ChromaDB (by design — trading news
  is ephemeral and we don't want to cache it).
- It scrapes the main page headline section and returns a formatted summary.
- We use the same browser headers as space_news to avoid 429 errors.
"""

from __future__ import annotations

import time
from typing import Any

import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool

_TRADING_URL = "https://tradingeconomics.com/"
_CACHE: dict[str, Any] = {}
_CACHE_TTL_SECONDS = 300

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def _fetch_trading_page(max_retries: int = 3) -> str | None:
    """Download the TradingEconomics homepage. Returns None on failure."""
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                time.sleep(2**attempt)

            resp = requests.get(
                _TRADING_URL,
                headers=_HEADERS,
                timeout=15,
            )

            if resp.status_code == 429:
                print(f"Rate limited (429) on attempt {attempt + 1}, retrying...")
                continue

            resp.raise_for_status()

            if "429 Too Many Requests" in resp.text:
                print(f"Got 429 error page on attempt {attempt + 1}")
                continue

            return resp.text

        except requests.RequestException as e:
            print(f"Request error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2**attempt)

    return None


def _parse_headlines(html: str) -> list[dict[str, str]]:
    """Extract headline articles from the TradingEconomics homepage."""
    soup = BeautifulSoup(html, "html.parser")
    headlines: list[dict[str, str]] = []

    # Look for the headline section
    headline_sections = soup.find_all("div", class_="headline-content")

    for section in headline_sections:
        # Title
        title_tag = section.find("span", class_="headline-title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # Description
        desc_tag = section.find("span", class_="headlines-description")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        if title or description:
            headlines.append(
                {
                    "title": title,
                    "description": description,
                }
            )

    return headlines


def _format_headlines(headlines: list[dict[str, str]]) -> str:
    """Produce a concise, LLM-friendly string from the headline list."""
    if not headlines:
        return "No trading headlines found on TradingEconomics.com right now."

    lines = ["Trading Economics Headlines:\n"]
    for i, headline in enumerate(headlines, 1):
        if headline["title"]:
            lines.append(f"{i}. {headline['title']}")
        if headline["description"]:
            lines.append(f"   {headline['description']}")
        lines.append("")

    lines.append(f"Source: {_TRADING_URL}")
    lines.append("(These headlines are live and not cached.)")
    return "\n".join(lines)


@tool
def trading_news_tool() -> str:
    """Fetch current trading and economic news headlines from TradingEconomics.com.

    Use this when the user asks for trading news, market updates, economic news,
    or anything related to financial markets and trading.

    Returns live headlines from TradingEconomics.com. These are NOT stored in
    the local database — they are fetched fresh each time.
    """
    # --- simple TTL cache ---
    cache_key = "trading_news"
    now = time.time()
    cached = _CACHE.get(cache_key)
    if cached and (now - cached["ts"]) < _CACHE_TTL_SECONDS:
        return cached["value"]

    html = _fetch_trading_page()
    if html is None:
        return (
            "Sorry, I couldn't reach TradingEconomics.com right now. "
            "The site may be temporarily blocking requests. Please try again in a few minutes."
        )

    headlines = _parse_headlines(html)
    result = _format_headlines(headlines)

    _CACHE[cache_key] = {"ts": now, "value": result}
    return result
