"""Tool registry for Dharampal.

All @tool-decorated functions are collected here so the agent can discover
and bind them dynamically. Adding a new tool is as simple as importing it
below and appending it to ALL_TOOLS.
"""

from dharampal.tools.space_news import space_news_tool
from dharampal.tools.news_search import search_historical_news
from dharampal.tools.news_scraper import scrape_historical_news
from dharampal.tools.trading_news import trading_news_tool
from dharampal.tools.list_sources import list_sources_tool

ALL_TOOLS = [
    space_news_tool,
    search_historical_news,
    scrape_historical_news,
    trading_news_tool,
    list_sources_tool,
]

__all__ = [
    "ALL_TOOLS",
    "space_news_tool",
    "search_historical_news",
    "scrape_historical_news",
    "trading_news_tool",
    "list_sources_tool",
]
