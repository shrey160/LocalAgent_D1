from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, ToolMessage

from dharampal.tools import ALL_TOOLS


class State(TypedDict):
    messages: Annotated[list, add_messages]


# Pre-compute the tool map for fast lookup in the tool node
tools_by_name = {t.name: t for t in ALL_TOOLS}


def get_model():
    return ChatOpenAI(
        model="friday-main", base_url="http://localhost:1234/v1", api_key="not-needed"
    )


def chatbot(state: State):
    """Invoke the LLM (with tools bound) and return its response."""
    llm = get_model()
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    # Ensure system message is present
    if not any(isinstance(m, SystemMessage) for m in state["messages"]):
        sys_msg = SystemMessage(
            content=(
                "You are Dharampal, a helpful AI assistant. Keep responses helpful and concise.\n\n"
                "TOOL USAGE RULES:\n"
                "1. space_news_tool — Use when the user asks for 'daily news', 'today's news', "
                "'yesterday's news', or 'recent space news'. This fetches articles from BOTH "
                "yesterday AND the day before yesterday (last 2 days).\n"
                "2. search_historical_news — Use when the user asks for news from a SPECIFIC date, "
                "e.g. 'April 21st', 'last Tuesday', 'March 15'. This searches the local memory first.\n"
                "3. scrape_historical_news — Use ONLY after search_historical_news when the user "
                "has explicitly said they want to check SpaceNews online (e.g. they replied 'yes').\n"
                "4. trading_news_tool — Use when the user asks for 'trading news', 'market updates', "
                "'economic news', or 'financial news'. This fetches live headlines from TradingEconomics.com. "
                "These are NOT cached locally.\n"
                "5. list_sources_tool — Use when the user asks about 'sources', 'what's cached', "
                "'where do you get news', or 'show me the sources'. This shows all available sources and cache status.\n"
                "6. tictactoe_tool — CRITICAL: Use for ALL tic-tac-toe interactions. "
                "Board uses numbers 1-9. User is X (first), you are O. "
                "When user sends ANY number 1-9 during a game, IMMEDIATELY call this tool with that number. "
                "Do not chat - just call the tool. Examples: '5' -> tictactoe_tool(move='5'), 'pick 3' -> tictactoe_tool(move='3'). "
                "After game ends, if user says 'yes'/'again', call tictactoe_tool to start new game.\n\n"
                "NEVER call scrape_historical_news without the user explicitly confirming they want "
                "to scrape. Always let search_historical_news handle the interaction first.\n\n"
                "ANTI-HALLUCINATION RULES:\n"
                "- You MUST ONLY report articles that are returned by the tools.\n"
                "- If a tool returns 'No articles found' or an error, tell the user honestly.\n"
                "- NEVER invent, makeup, or guess article titles, dates, or content.\n"
                "- If you don't have news for a date, say so clearly.\n"
                "- Do not say 'Here are some articles' unless the tool actually returned articles."
            )
        )
        messages = [sys_msg] + state["messages"]
    else:
        messages = state["messages"]

    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def tool_node(state: State):
    """Execute any tool calls requested by the LLM."""
    result_messages = []
    last_message = state["messages"][-1]

    # Tool calls are attached to AIMessage objects
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return {"messages": []}

    for tool_call in last_message.tool_calls:
        tool_name = tool_call.get("name")
        tool_args = tool_call.get("args", {})
        tool_id = tool_call.get("id")

        tool = tools_by_name.get(tool_name)
        if tool is None:
            observation = f"Error: tool '{tool_name}' not found."
        else:
            try:
                observation = tool.invoke(tool_args)
            except Exception as e:
                observation = f"Error running tool '{tool_name}': {e}"

        result_messages.append(
            ToolMessage(content=str(observation), tool_call_id=tool_id)
        )

    return {"messages": result_messages}


def should_continue(state: State):
    """Route to 'tools' if the LLM requested tool calls, else END."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


# Build graph
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", tool_node)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges(
    "chatbot", should_continue, {"tools": "tools", END: END}
)
graph_builder.add_edge("tools", "chatbot")

# Memory
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
app_with_memory = graph_builder.compile(checkpointer=memory)

thread_config = {"configurable": {"thread_id": "1"}}


def get_response(user_input: str) -> str:
    events = app_with_memory.invoke(
        {"messages": [("user", user_input)]}, config=thread_config
    )
    return events["messages"][-1].content
