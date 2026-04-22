from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

class State(TypedDict):
    messages: Annotated[list, add_messages]

def get_model():
    return ChatOpenAI(
        model="friday-main",
        base_url="http://localhost:1234/v1",
        api_key="not-needed"
    )

def chatbot(state: State):
    llm = get_model()
    # Ensure system message is included
    if not any(isinstance(m, SystemMessage) for m in state["messages"]):
        sys_msg = SystemMessage(content="You are Dharampal, a helpful AI assistant. Keep responses helpful and concise.")
        messages = [sys_msg] + state["messages"]
    else:
        messages = state["messages"]
        
    response = llm.invoke(messages)
    return {"messages": [response]}

graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()
app_with_memory = graph_builder.compile(checkpointer=memory)

thread_config = {"configurable": {"thread_id": "1"}}

def get_response(user_input: str) -> str:
    events = app_with_memory.invoke(
        {"messages": [("user", user_input)]},
        config=thread_config
    )
    return events["messages"][-1].content
