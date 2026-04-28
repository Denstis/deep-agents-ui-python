# Simple LangGraph agent example for local development
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import add_messages
import os
import httpx


# Define the state schema
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


def get_lmstudio_url() -> str:
    """Get LM Studio URL from environment or use default."""
    return os.getenv("LMSTUDIO_URL", "http://localhost:1234")


async def call_lmstudio(messages: list[dict]) -> str:
    """Call LM Studio API to generate a response."""
    lmstudio_url = get_lmstudio_url()
    
    # Convert LangChain messages to LM Studio format
    formatted_messages = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            formatted_messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            formatted_messages.append({"role": "assistant", "content": msg.content})
        else:
            formatted_messages.append({"role": "user", "content": str(msg)})
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{lmstudio_url}/v1/chat/completions",
                json={
                    "messages": formatted_messages,
                    "temperature": 0.7,
                    "max_tokens": 1024,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error calling LM Studio: {str(e)}"


# Define the node function (sync version for LangGraph)
def call_model(state: AgentState) -> dict:
    """Call LM Studio to generate a response."""
    import asyncio
    
    last_message = state["messages"][-1] if state["messages"] else None
    
    if last_message and isinstance(last_message, HumanMessage):
        # Convert messages to list of dicts for LM Studio
        messages_list = []
        for msg in state["messages"]:
            if isinstance(msg, HumanMessage):
                messages_list.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                messages_list.append({"role": "assistant", "content": msg.content})
        
        # Call LM Studio synchronously
        try:
            lmstudio_url = get_lmstudio_url()
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{lmstudio_url}/v1/chat/completions",
                    json={
                        "messages": messages_list,
                        "temperature": 0.7,
                        "max_tokens": 1024,
                    },
                )
                response.raise_for_status()
                data = response.json()
                ai_content = data["choices"][0]["message"]["content"]
                return {"messages": [AIMessage(content=ai_content)]}
        except Exception as e:
            error_msg = f"Error calling LM Studio: {str(e)}"
            return {"messages": [AIMessage(content=error_msg)]}
    
    return {"messages": [AIMessage(content="Hello! I'm a simple test agent.")]}


# Build the graph
workflow = StateGraph(AgentState)

# Add the node
workflow.add_node("agent", call_model)

# Set the entry point
workflow.add_edge(START, "agent")

# Set the finish point
workflow.add_edge("agent", END)

# Compile the graph
graph = workflow.compile()

if __name__ == "__main__":
    # Test the graph
    result = graph.invoke({"messages": [HumanMessage(content="Hello!")]})
    print(result)
