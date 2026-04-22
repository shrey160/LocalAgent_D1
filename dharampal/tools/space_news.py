"""Space News scraper tool.

Fetches yesterday's articles from the SpaceNews archive and returns them
as a formatted string suitable for an LLM context window.

Design notes (for reviewer):
- We scrape the archive listing page and extract article cards. Each card
  contains a title, date, excerpt, and URL.
- The target date is "yesterday" relative to the system clock at call time.
- If the site structure changes, _parse_articles() will return an empty list
  and the tool politely reports that no articles were found (rather than
  crashing the agent loop).
- A small in-process cache (5 min TTL) prevents repeated scrapes within a
  single agent conversation.
"""

from __future__ import annotations

import datetime
import textwrap
import time
from typing import Any

import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool

_ARCHIVE_URL = "https://spacenews.com/section/news-archive/"
_CACHE: dict[str, Any] = {}
_CACHE_TTL_SECONDS = 300


def _fetch_archive() -> str | None:
    """Download the archive page HTML. Returns None on failure."""
    try:
        resp = requests.get(_ARCHIVE_URL, timeout=15)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException:
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
        if art["excerpt"]:
            # Keep excerpts short so they don't blow up the context window
            excerpt = textwrap.shorten(art["excerpt"], width=180, placeholder="...")
            lines.append(f"   Excerpt: {excerpt}")
        if art["url"]:
            lines.append(f"   URL: {art['url']}")
        lines.append("")
    return "\n".join(lines)


@tool
def space_news_tool() -> str:
    """Fetch yesterday's space news articles from SpaceNews.

    Use this when the user asks for daily news, space news, recent headlines,
    or anything similar. Returns a formatted summary of articles published
    on the previous calendar day.
    """
    # --- simple TTL cache ---
    cache_key = "space_news_yesterday"
    now = time.time()
    cached = _CACHE.get(cache_key)
    if cached and (now - cached["ts"]) < _CACHE_TTL_SECONDS:
        return cached["value"]

    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    html = _fetch_archive()
    if html is None:
        return "Sorry, I couldn't reach the SpaceNews archive right now. Please try again later."

    articles = _parse_articles(html, yesterday)
    result = _format_articles(articles, yesterday)

    _CACHE[cache_key] = {"ts": now, "value": result}
    return result
