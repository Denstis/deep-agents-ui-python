# Simple LangGraph agent example for local development
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import add_messages


# Define the state schema
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


# Define the node function
def call_model(state: AgentState) -> dict:
    """Simple echo model for testing."""
    last_message = state["messages"][-1] if state["messages"] else None
    
    if last_message and isinstance(last_message, HumanMessage):
        response = f"Echo: {last_message.content}"
        return {"messages": [AIMessage(content=response)]}
    
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
