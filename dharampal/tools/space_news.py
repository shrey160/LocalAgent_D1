"""Space News scraper tool.

Fetches the last two days of articles from the SpaceNews archive (yesterday
and day before yesterday) and returns them as a formatted string suitable
for an LLM context window.

Design notes (for reviewer):
- We scrape the archive listing page once and extract article cards for both
  target dates. Each card contains a title, date, excerpt, and URL.
- The target dates are "yesterday" and "day before yesterday" relative to
  the system clock at call time.
- If the site structure changes, _parse_articles() will return an empty list
  and the tool politely reports that no articles were found (rather than
  crashing the agent loop).
- A small in-process cache (5 min TTL) prevents repeated scrapes within a
  single agent conversation.
- Articles are automatically persisted to ChromaDB so they can be retrieved
  later via `search_historical_news`.
- If SpaceNews is rate-limiting us (429), the tool falls back to checking
  the local ChromaDB for cached articles from the target dates.
"""

from __future__ import annotations

import datetime
import subprocess
import textwrap
import time
from typing import Any

from bs4 import BeautifulSoup
from langchain_core.tools import tool

from dharampal.storage.chroma_store import ChromaNewsStore

_ARCHIVE_URL = "https://spacenews.com/section/news-archive/"
_CACHE: dict[str, Any] = {}
_CACHE_TTL_SECONDS = 300
_store = ChromaNewsStore()


def _fetch_archive(max_retries: int = 3) -> str | None:
    """Download the archive page HTML via curl subprocess. Returns None on failure.

    We use curl instead of requests because SpaceNews aggressively rate-limits
    Python requests (HTTP 429) but allows curl from the terminal.
    """
    for attempt in range(max_retries):
        if attempt > 0:
            time.sleep(2**attempt)

        try:
            result = subprocess.run(
                [
                    "curl",
                    "-s",  # silent
                    "-L",  # follow redirects
                    "-A",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "-H",
                    "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "-H",
                    "Accept-Language: en-US,en;q=0.5",
                    "--compressed",
                    "--max-time",
                    "15",
                    _ARCHIVE_URL,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=20,
            )

            if result.returncode != 0:
                print(f"curl failed (code {result.returncode}): {result.stderr[:200]}")
                continue

            html = result.stdout

            if not html or "429 Too Many Requests" in html:
                print(f"Got 429 on attempt {attempt + 1}")
                continue

            return html

        except Exception as e:
            print(f"Error on attempt {attempt + 1}: {e}")

    return None


def _parse_articles(html: str, target_date: datetime.date) -> list[dict[str, str]]:
    """Extract articles whose visible date matches *target_date*.

    SpaceNews archive cards typically look like:

        <article class="archive-item">
            <h2 class="entry-title"><a href="...">Title</a></h2>
            <span class="entry-date">April 21, 2026</span>
            <div class="entry-summary">Excerpt ...</div>
        </article>

    We are lenient: if the date string contains the target month *and* day
    (and optionally year), we consider it a match. This avoids brittleness
    around year boundaries or slight formatting drift.
    """
    soup = BeautifulSoup(html, "html.parser")
    articles: list[dict[str, str]] = []

    # Try the most common container first, then fall back to generic <article>
    containers = soup.find_all("article", class_="archive-item")
    if not containers:
        containers = soup.find_all("article")

    target_month_day = target_date.strftime("%B %d").lstrip("0")
    target_month_day_short = target_date.strftime("%b %d").lstrip("0")

    for article in containers:
        # --- title & url ---
        title_tag = article.find("h2", class_="entry-title")
        if not title_tag:
            title_tag = article.find("h2")
        link = title_tag.find("a") if title_tag else None
        title = (
            link.get_text(strip=True)
            if link
            else (title_tag.get_text(strip=True) if title_tag else "")
        )
        url = link["href"] if link and link.has_attr("href") else ""

        if not title:
            continue

        # --- date ---
        date_tag = article.find("span", class_="entry-date")
        if not date_tag:
            date_tag = article.find("time")
        date_text = date_tag.get_text(strip=True) if date_tag else ""

        # --- excerpt ---
        summary_tag = article.find("div", class_="entry-summary")
        if not summary_tag:
            # Some archive pages use <p> directly inside the article
            paragraphs = article.find_all("p")
            summary_tag = paragraphs[0] if paragraphs else None
        excerpt = summary_tag.get_text(strip=True) if summary_tag else ""

        # --- filtering ---
        if target_month_day in date_text or target_month_day_short in date_text:
            articles.append(
                {
                    "title": title,
                    "date": date_text,
                    "url": url,
                    "excerpt": excerpt,
                }
            )

    return articles


def _format_articles(articles: list[dict[str, str]], target_date: datetime.date) -> str:
    """Produce a concise, LLM-friendly string from the article list."""
    if not articles:
        return f"No SpaceNews articles found for {target_date.strftime('%B %d, %Y')}."

    lines = [f"SpaceNews articles from {target_date.strftime('%B %d, %Y')}:\n"]
    for i, art in enumerate(articles, 1):
        lines.append(f"{i}. {art['title']}")
        lines.append(f"   Date: {art['date']}")
        if art.get("excerpt"):
            # Keep excerpts short so they don't blow up the context window
            excerpt = textwrap.shorten(art["excerpt"], width=180, placeholder="...")
            lines.append(f"   Excerpt: {excerpt}")
        if art.get("url"):
            lines.append(f"   URL: {art['url']}")
        lines.append("")
    return "\n".join(lines)


def _format_db_articles(articles: list[dict], target_date: datetime.date) -> str:
    """Format articles retrieved from ChromaDB (different key names)."""
    if not articles:
        return f"No cached articles for {target_date.strftime('%B %d, %Y')}."

    lines = [f"SpaceNews articles from {target_date.strftime('%B %d, %Y')} (cached):\n"]
    for i, art in enumerate(articles, 1):
        lines.append(f"{i}. {art['title']}")
        lines.append(f"   Date: {art['date']}")
        if art.get("excerpt"):
            excerpt = textwrap.shorten(art["excerpt"], width=180, placeholder="...")
            lines.append(f"   Excerpt: {excerpt}")
        if art.get("url"):
            lines.append(f"   URL: {art['url']}")
        lines.append("")
    return "\n".join(lines)


@tool
def space_news_tool() -> str:
    """Fetch the last two days of space news articles from SpaceNews.

    Use this when the user asks for daily news, space news, recent headlines,
    or anything similar. Returns a formatted summary of articles published
    on yesterday AND the day before yesterday.
    """
    # --- simple TTL cache ---
    cache_key = "space_news_daily"
    now = time.time()
    cached = _CACHE.get(cache_key)
    if cached and (now - cached["ts"]) < _CACHE_TTL_SECONDS:
        return cached["value"]

    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    day_before = today - datetime.timedelta(days=2)

    # Fetch archive page once (efficient for both dates)
    html = _fetch_archive()

    if html is None:
        # Fallback: check local DB for both dates
        db_articles_yesterday = _store.search_by_date(yesterday.strftime("%B %d, %Y"))
        db_articles_day_before = _store.search_by_date(day_before.strftime("%B %d, %Y"))

        if db_articles_yesterday or db_articles_day_before:
            result_parts = []
            if db_articles_yesterday:
                result_parts.append(
                    _format_db_articles(db_articles_yesterday, yesterday)
                )
            if db_articles_day_before:
                result_parts.append(
                    _format_db_articles(db_articles_day_before, day_before)
                )
            result = "\n\n".join(result_parts)
            result += "\n\n(Note: SpaceNews is temporarily unavailable, showing cached articles.)"
            _CACHE[cache_key] = {"ts": now, "value": result}
            return result
        else:
            return (
                "Sorry, I couldn't reach the SpaceNews archive right now, "
                "and I don't have any cached articles for the last two days. "
                "Please try again in a few minutes."
            )

    # Parse articles for both dates from single HTML fetch
    articles_yesterday = _parse_articles(html, yesterday)
    articles_day_before = _parse_articles(html, day_before)

    # Persist to ChromaDB for future historical queries
    total_new = 0
    if articles_yesterday:
        total_new += _store.add_articles(articles_yesterday)
    if articles_day_before:
        total_new += _store.add_articles(articles_day_before)

    # Build combined result
    result_parts = []
    if articles_yesterday:
        result_parts.append(_format_articles(articles_yesterday, yesterday))
    if articles_day_before:
        result_parts.append(_format_articles(articles_day_before, day_before))

    if not result_parts:
        result = (
            f"No SpaceNews articles found for {yesterday.strftime('%B %d')} "
            f"or {day_before.strftime('%B %d')}."
        )
    else:
        result = "\n\n".join(result_parts)
        if total_new:
            result += f"\n\n(I've saved {total_new} new article(s) to my local memory.)"

    _CACHE[cache_key] = {"ts": now, "value": result}
    return result
