"""Tool registry for Dharampal.

All @tool-decorated functions are collected here so the agent can discover
and bind them dynamically. Adding a new tool is as simple as importing it
below and appending it to ALL_TOOLS.
"""

from dharampal.tools.space_news import space_news_tool

ALL_TOOLS = [space_news_tool]

__all__ = ["ALL_TOOLS", "space_news_tool"]
