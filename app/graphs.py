"""Multi-agent graphs for different tasks.

This module provides various LangGraph-based agent configurations:
- Research Agent: Web search and information gathering
- Coding Agent: Python code execution and file operations
- System Agent: Command line and system operations
- Data Agent: Data processing and analysis
- Supervisor: Multi-agent orchestration
"""

from typing import Annotated, Sequence, TypedDict, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
import os
import httpx


# ============================================================================
# Shared State Definitions
# ============================================================================

class AgentState(TypedDict):
    """Base state for all agents."""
    messages: Annotated[Sequence[BaseMessage], add_messages]


class ResearchState(TypedDict):
    """State for research agent with search context."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    search_queries: list[str]
    search_results: list[dict]
    current_topic: str


class CodingState(TypedDict):
    """State for coding agent with execution context."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    code_snippets: list[str]
    execution_results: list[dict]
    files_modified: list[str]


class SystemState(TypedDict):
    """State for system agent with command context."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    commands_executed: list[str]
    command_results: list[dict]


class DataState(TypedDict):
    """State for data processing agent."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    data_files: list[str]
    analysis_results: list[dict]
    visualizations: list[str]


# ============================================================================
# Helper Functions
# ============================================================================

def get_lmstudio_url() -> str:
    """Get LM Studio URL from environment or use default."""
    return os.getenv("LMSTUDIO_URL", "http://localhost:1234")


def call_llm_sync(messages: list, system_prompt: str = "") -> str:
    """Call LM Studio API synchronously."""
    lmstudio_url = get_lmstudio_url()
    
    formatted_messages = []
    if system_prompt:
        formatted_messages.append({"role": "system", "content": system_prompt})
    
    for msg in messages:
        if isinstance(msg, HumanMessage):
            formatted_messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            formatted_messages.append({"role": "assistant", "content": msg.content})
        elif isinstance(msg, SystemMessage):
            formatted_messages.append({"role": "system", "content": msg.content})
        else:
            formatted_messages.append({"role": "user", "content": str(msg)})
    
    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{lmstudio_url}/v1/chat/completions",
                json={
                    "messages": formatted_messages,
                    "temperature": 0.7,
                    "max_tokens": 2048,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error calling LLM: {str(e)}"


# ============================================================================
# Research Agent Graph
# ============================================================================

def create_research_agent():
    """Create a research agent with web search capabilities."""
    from app.tools.internet import web_search, fetch_url, duckduckgo_search
    
    # Define tools
    research_tools = [web_search, fetch_url, duckduckgo_search]
    
    class ResearchAgentState(TypedDict):
        messages: Annotated[Sequence[BaseMessage], add_messages]
        search_history: list[str]
        findings: list[str]
    
    def research_node(state: ResearchAgentState) -> dict:
        """Research agent node that decides on search queries."""
        system_prompt = """You are a research assistant with access to web search tools.
Your task is to find accurate and up-to-date information on the user's topic.

Available tools:
- web_search: Search the web using Tavily API
- duckduckgo_search: Free web search alternative
- fetch_url: Fetch and parse content from a specific URL

When researching:
1. Break down complex questions into specific search queries
2. Use multiple searches to gather comprehensive information
3. Verify information from multiple sources
4. Cite your sources with URLs
5. Summarize findings clearly and concisely

Always explain your search strategy before executing searches."""
        
        last_message = state["messages"][-1].content if state["messages"] else ""
        
        # Check if we need to search or provide final answer
        if "search" in last_message.lower() or "?" in last_message:
            # Let the model decide on search queries
            response = call_llm_sync(state["messages"], system_prompt)
        else:
            response = call_llm_sync(state["messages"], system_prompt)
        
        return {"messages": [AIMessage(content=response)]}
    
    # Build graph
    workflow = StateGraph(ResearchAgentState)
    workflow.add_node("researcher", research_node)
    workflow.add_edge(START, "researcher")
    workflow.add_edge("researcher", END)
    
    return workflow.compile()


# ============================================================================
# Coding Agent Graph
# ============================================================================

def create_coding_agent():
    """Create a coding agent with Python execution capabilities."""
    from app.tools.python_tools import execute_python, execute_python_in_subprocess
    from app.tools.filesystem import read_file, write_file, list_directory
    from app.tools.pip_tools import install_package, list_packages
    
    class CodingAgentState(TypedDict):
        messages: Annotated[Sequence[BaseMessage], add_messages]
        code_history: list[str]
        files_created: list[str]
        packages_installed: list[str]
    
    def coding_node(state: CodingAgentState) -> dict:
        """Coding agent node that writes and executes code."""
        system_prompt = """You are an expert Python programmer with access to code execution tools.

Available tools:
- execute_python: Run Python code directly
- execute_python_in_subprocess: Run Python in isolated subprocess
- read_file: Read file contents
- write_file: Create or modify files
- list_directory: List directory contents
- install_package: Install Python packages
- list_packages: List installed packages

Guidelines:
1. Write clean, well-commented code
2. Test code incrementally
3. Handle errors gracefully
4. Follow Python best practices (PEP 8)
5. Document your code with docstrings
6. Use type hints where appropriate

Before executing code, explain what it does and any potential risks."""
        
        response = call_llm_sync(state["messages"], system_prompt)
        return {"messages": [AIMessage(content=response)]}
    
    workflow = StateGraph(CodingAgentState)
    workflow.add_node("coder", coding_node)
    workflow.add_edge(START, "coder")
    workflow.add_edge("coder", END)
    
    return workflow.compile()


# ============================================================================
# System Agent Graph
# ============================================================================

def create_system_agent():
    """Create a system agent for command line operations."""
    from app.tools.command_line import execute_command, run_python_script
    from app.tools.network import ping_host, port_scan, get_network_info
    from app.tools.filesystem import list_directory, file_exists, get_file_info
    
    class SystemAgentState(TypedDict):
        messages: Annotated[Sequence[BaseMessage], add_messages]
        commands_run: list[str]
        system_info: dict
    
    def system_node(state: SystemAgentState) -> dict:
        """System agent node for administrative tasks."""
        system_prompt = """You are a system administrator assistant with command line access.

Available tools:
- execute_command: Run shell commands
- run_python_script: Execute Python scripts
- ping_host: Check network connectivity
- port_scan: Scan open ports on a host
- get_network_info: Get network configuration
- list_directory: List directory contents
- file_exists: Check if file exists
- get_file_info: Get file metadata

Security Guidelines:
1. NEVER execute destructive commands (rm -rf, format, etc.)
2. ALWAYS explain commands before running them
3. Use read-only commands when possible
4. Warn about potentially dangerous operations
5. Respect system boundaries and permissions

Provide clear explanations of command outputs and their implications."""
        
        response = call_llm_sync(state["messages"], system_prompt)
        return {"messages": [AIMessage(content=response)]}
    
    workflow = StateGraph(SystemAgentState)
    workflow.add_node("sysadmin", system_node)
    workflow.add_edge(START, "sysadmin")
    workflow.add_edge("sysadmin", END)
    
    return workflow.compile()


# ============================================================================
# Data Analysis Agent Graph
# ============================================================================

def create_data_agent():
    """Create a data analysis agent."""
    from app.tools.python_tools import execute_python
    from app.tools.filesystem import read_file, write_file, list_directory
    
    class DataAgentState(TypedDict):
        messages: Annotated[Sequence[BaseMessage], add_messages]
        datasets_loaded: list[str]
        analysis_code: list[str]
        results: list[dict]
    
    def data_node(state: DataAgentState) -> dict:
        """Data analysis agent node."""
        system_prompt = """You are a data scientist assistant specializing in data analysis.

Available tools:
- execute_python: Run Python code for data analysis
- read_file: Load data files (CSV, JSON, etc.)
- write_file: Save analysis results
- list_directory: Find data files

Common libraries available:
- pandas: Data manipulation
- numpy: Numerical computing
- matplotlib/seaborn: Visualization
- scikit-learn: Machine learning

Workflow:
1. Explore and understand the data
2. Clean and preprocess as needed
3. Perform statistical analysis
4. Create visualizations
5. Draw insights and conclusions

Always explain your analysis steps and interpret results clearly."""
        
        response = call_llm_sync(state["messages"], system_prompt)
        return {"messages": [AIMessage(content=response)]}
    
    workflow = StateGraph(DataAgentState)
    workflow.add_node("analyst", data_node)
    workflow.add_edge(START, "analyst")
    workflow.add_edge("analyst", END)
    
    return workflow.compile()


# ============================================================================
# Multi-Agent Supervisor Graph (Orchestrator)
# ============================================================================

def create_supervisor_agent():
    """Create a supervisor that coordinates multiple specialized agents.
    
    The orchestrator:
    1. Analyzes incoming tasks using keyword matching + LLM fallback
    2. Determines which specialized agent is best suited
    3. Delegates the task by invoking the actual agent graph
    4. Collects and reviews agent outputs
    5. Provides comprehensive response to user
    """
    
    # Create specialized agent graphs at orchestrator creation time
    research_graph = create_research_agent()
    coding_graph = create_coding_agent()
    system_graph = create_system_agent()
    data_graph = create_data_agent()
    
    class SupervisorState(TypedDict):
        messages: Annotated[Sequence[BaseMessage], add_messages]
        current_agent: str
        agent_outputs: dict[str, str]
        task_delegated: bool
        delegation_history: list[str]
        remaining_steps: int
    
    def supervisor_node(state: SupervisorState) -> dict:
        """Supervisor that analyzes requests and routes to appropriate agents.
        
        Uses keyword-based routing with Russian and English keywords.
        Falls back to LLM for ambiguous cases.
        """
        last_message = state["messages"][-1].content if state["messages"] else ""
        last_message_lower = last_message.lower()
        
        # Routing scores
        agent_scores = {"researcher": 0, "coder": 0, "sysadmin": 0, "analyst": 0}
        
        # Research keywords (Russian + English)
        for kw in ["найди", "поиск", "найти", "search", "find", "look up", 
                   "what is", "who is", "узнай", "новости", "news", 
                   "wikipedia", "википедия", "информация", "information",
                   "исследуй", "research", "расскажи о", "tell me about",
                   "что такое", "кто такой"]:
            if kw in last_message_lower:
                agent_scores["researcher"] += 3
        
        # Coding keywords
        for kw in ["код", "code", "python", "программ", "program",
                   "скрипт", "script", "функция", "function",
                   "отладк", "debug", "напиши код", "write code",
                   "разработ", "develop", "реализ", "implement",
                   "автоматиз", "automate", "исправь ошибку"]:
            if kw in last_message_lower:
                agent_scores["coder"] += 3
                
        # Sysadmin keywords
        for kw in ["команд", "command", "сервер", "server",
                   "сеть", "network", "пинг", "ping",
                   "файл", "file", "директор", "directory",
                   "систем", "system", "linux", "bash", "shell",
                   "запусти", "run", "exec", "ls ", "pwd", "cd "]:
            if kw in last_message_lower:
                agent_scores["sysadmin"] += 3
                
        # Analyst keywords
        for kw in ["анализ", "analyze", "данные", "data",
                   "статистик", "statistics", "график", "chart",
                   "визуализ", "visualization", "pandas", "dataframe",
                   "построй график", "plot", "диаграмм"]:
            if kw in last_message_lower:
                agent_scores["analyst"] += 3
        
        # Select best agent
        selected_agent = max(agent_scores, key=agent_scores.get)
        max_score = agent_scores[selected_agent]
        
        # Fallback to LLM if no keywords matched
        if max_score == 0:
            system_prompt = """You are an intelligent orchestrator. Analyze the user's request and determine which specialist agent should handle it.

RESPOND WITH ONLY ONE WORD from: RESEARCHER, CODER, SYSADMIN, ANALYST

Agent capabilities:
- RESEARCHER: Web search, information gathering, fact-checking, news, general knowledge
- CODER: Python programming, code execution, file operations, debugging
- SYSADMIN: Shell commands, network diagnostics, system management
- ANALYST: Data analysis, statistics, visualization"""
            
            llm_response = call_llm_sync(state["messages"], system_prompt)
            llm_lower = llm_response.lower().strip()
            
            if "researcher" in llm_lower or "research" in llm_lower:
                selected_agent = "researcher"
            elif "coder" in llm_lower or "code" in llm_lower:
                selected_agent = "coder"
            elif "sysadmin" in llm_lower or "system" in llm_lower:
                selected_agent = "sysadmin"
            elif "analyst" in llm_lower or "data" in llm_lower or "analysis" in llm_lower:
                selected_agent = "analyst"
            else:
                selected_agent = "researcher"
        
        # Track delegation
        delegation_history = state.get("delegation_history", [])
        delegation_history.append(f"Step {len(delegation_history)+1}: Routing to {selected_agent}")
        
        return {
            "messages": state["messages"],
            "current_agent": selected_agent,
            "task_delegated": True,
            "agent_outputs": state.get("agent_outputs", {}),
            "delegation_history": delegation_history,
            "remaining_steps": 1,
        }
    
    def delegate_to_agent(state: SupervisorState) -> dict:
        """Delegate task to the selected specialized agent and execute its graph."""
        agent_name = state.get("current_agent", "researcher")
        
        # Map agent names to their graphs
        agent_graphs = {
            "researcher": research_graph,
            "coder": coding_graph,
            "sysadmin": system_graph,
            "analyst": data_graph,
        }
        
        if agent_name not in agent_graphs:
            return {
                "messages": [AIMessage(content=f"Error: Unknown agent '{agent_name}'")],
                "agent_outputs": {agent_name: "Error - unknown agent"},
            }
        
        agent_input = {"messages": state["messages"]}
        
        try:
            # Execute the specialized agent's graph
            agent_graph = agent_graphs[agent_name]
            result = agent_graph.invoke(agent_input)
            
            # Extract response
            agent_messages = result.get("messages", [])
            agent_response = ""
            if agent_messages:
                last_msg = agent_messages[-1]
                agent_response = str(last_msg.content) if hasattr(last_msg, 'content') else str(last_msg)
            
            # Log delegation
            delegation_msg = f"✅ Delegated to {agent_name.upper()} agent.\n\n📋 Agent response:\n{agent_response}"
            
            # Update state
            agent_outputs = state.get("agent_outputs", {})
            agent_outputs[agent_name] = agent_response
            
            delegation_history = state.get("delegation_history", [])
            delegation_history.append(f"Completed: {agent_name}")
            
            return {
                "messages": [AIMessage(content=delegation_msg)],
                "agent_outputs": agent_outputs,
                "delegation_history": delegation_history,
                "remaining_steps": state.get("remaining_steps", 1) - 1,
            }
            
        except Exception as e:
            error_msg = f"❌ Error executing {agent_name} agent: {str(e)}"
            return {
                "messages": [AIMessage(content=error_msg)],
                "agent_outputs": {agent_name: f"Error: {str(e)}"},
            }
    
    def should_continue(state: SupervisorState) -> Literal["delegate", "finalize", "end"]:
        """Decide next step based on remaining steps and outputs."""
        remaining = state.get("remaining_steps", 0)
        
        if remaining > 0 and state.get("task_delegated"):
            return "delegate"
        elif remaining <= 0 and state.get("agent_outputs"):
            return "finalize"
        return "end"
    
    def finalize_node(state: SupervisorState) -> dict:
        """Finalize multi-agent workflow with comprehensive response."""
        agent_outputs = state.get("agent_outputs", {})
        delegation_history = state.get("delegation_history", [])
        
        final_response = "🎯 **Task Completed by Orchestrator**\n\n"
        final_response += "📝 **Execution Summary:**\n"
        for step in delegation_history:
            final_response += f"- {step}\n"
        
        final_response += "\n📊 **Agent Outputs:**\n"
        for agent, output in agent_outputs.items():
            final_response += f"\n**{agent.upper()}:**\n{output}\n"
        
        return {"messages": [AIMessage(content=final_response)]}
    
    # Build workflow graph
    workflow = StateGraph(SupervisorState)
    
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("delegate", delegate_to_agent)
    workflow.add_node("finalize", finalize_node)
    
    workflow.add_edge(START, "supervisor")
    
    workflow.add_conditional_edges(
        "supervisor",
        should_continue,
        {"delegate": "delegate", "finalize": "finalize", "end": END}
    )
    
    workflow.add_conditional_edges(
        "delegate",
        should_continue,
        {"delegate": "delegate", "finalize": "finalize", "end": END}
    )
    
    workflow.add_edge("finalize", END)
    
    return workflow.compile()


# ============================================================================
# Universal Agent with All Tools
# ============================================================================

def create_universal_agent():
    """Create a universal agent with access to all tools."""
    from app.tools.internet import web_search, fetch_url, duckduckgo_search
    from app.tools.filesystem import (
        read_file, write_file, list_directory, 
        delete_file, create_directory, file_exists
    )
    from app.tools.command_line import execute_command
    from app.tools.python_tools import execute_python
    from app.tools.pip_tools import install_package, list_packages
    from app.tools.network import ping_host, http_request, get_network_info
    
    # Comprehensive tool list
    all_tools = [
        # Internet
        web_search, fetch_url, duckduckgo_search,
        # Filesystem
        read_file, write_file, list_directory, 
        delete_file, create_directory, file_exists,
        # Command line
        execute_command,
        # Python
        execute_python,
        # Pip
        install_package, list_packages,
        # Network
        ping_host, http_request, get_network_info,
    ]
    
    class UniversalState(TypedDict):
        messages: Annotated[Sequence[BaseMessage], add_messages]
        tools_used: list[str]
        task_complete: bool
    
    def universal_node(state: UniversalState) -> dict:
        """Universal agent with all capabilities."""
        system_prompt = """You are a versatile AI assistant with comprehensive tool access.

AVAILABLE TOOLS:

📡 Internet Tools:
- web_search(query, max_results, topic): Search the web
- fetch_url(url): Fetch webpage content
- duckduckgo_search(query): Alternative web search

📁 Filesystem Tools:
- read_file(file_path): Read file contents
- write_file(file_path, content): Create/modify files
- list_directory(dir_path): List directory contents
- delete_file(file_path): Delete a file
- create_directory(dir_path): Create a directory
- file_exists(path): Check if path exists

💻 Command Line:
- execute_command(command, timeout): Run shell commands

🐍 Python Execution:
- execute_python(code): Run Python code

📦 Package Management:
- install_package(package): Install Python packages
- list_packages(): List installed packages

🌐 Network Tools:
- ping_host(host): Check network connectivity
- http_request(url, method, headers, data): Make HTTP requests
- get_network_info(): Get network configuration

GUIDELINES:
1. Choose the right tool for each task
2. Explain your actions before executing
3. Handle errors gracefully
4. Keep security in mind (especially with commands/code)
5. Provide clear, helpful responses

APPROACH:
1. Understand the user's request
2. Plan your approach (which tools to use)
3. Execute step by step
4. Verify results
5. Summarize outcomes"""
        
        response = call_llm_sync(state["messages"], system_prompt)
        return {
            "messages": [AIMessage(content=response)],
            "tools_used": [],
            "task_complete": False,
        }
    
    workflow = StateGraph(UniversalState)
    workflow.add_node("universal_agent", universal_node)
    workflow.add_edge(START, "universal_agent")
    workflow.add_edge("universal_agent", END)
    
    return workflow.compile()


# ============================================================================
# Export Factory Functions
# ============================================================================

def get_agent(agent_type: str = "supervisor"):
    """Factory function to get an agent by type.
    
    Args:
        agent_type: Type of agent ("research", "coding", "system", "data", "supervisor"/"orchestrator", "universal")
    
    Returns:
        Compiled LangGraph agent
    """
    agents = {
        "research": create_research_agent,
        "coding": create_coding_agent,
        "system": create_system_agent,
        "data": create_data_agent,
        "supervisor": create_supervisor_agent,
        "orchestrator": create_supervisor_agent,  # Alias for supervisor
        "universal": create_universal_agent,
    }
    
    if agent_type not in agents:
        raise ValueError(f"Unknown agent type: {agent_type}. Available: {list(agents.keys())}")
    
    return agents[agent_type]()


# Backward compatibility - keep original simple graph
def create_simple_agent():
    """Create the original simple agent for backward compatibility."""
    from app.agent import graph as original_graph
    return original_graph


__all__ = [
    "create_research_agent",
    "create_coding_agent",
    "create_system_agent",
    "create_data_agent",
    "create_supervisor_agent",
    "create_universal_agent",
    "get_agent",
    "AgentState",
    "ResearchState",
    "CodingState",
    "SystemState",
    "DataState",
]
