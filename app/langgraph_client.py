"""LangGraph client wrapper for connecting to LangGraph deployments."""

from typing import Optional, Any, AsyncGenerator
import httpx
from langgraph_sdk import get_client


def normalize_url(url: str) -> str:
    """Ensure URL has http:// or https:// prefix."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    return url


class LangGraphClientWrapper:
    """Wrapper around LangGraph SDK client for async operations."""
    
    def __init__(self, deployment_url: str, api_key: Optional[str] = None):
        self.deployment_url = normalize_url(deployment_url)
        self.api_key = api_key
        # Only pass api_key if it's provided and not empty
        client_kwargs = {"url": self.deployment_url}
        if api_key and api_key.strip():
            client_kwargs["api_key"] = api_key
        self.client = get_client(**client_kwargs)
    
    async def get_assistant(self, assistant_id: str) -> dict[str, Any]:
        """Get assistant by ID."""
        try:
            return await self.client.assistants.get(assistant_id)
        except Exception as e:
            # Return a default assistant structure if fetch fails
            return {
                "assistant_id": assistant_id,
                "graph_id": assistant_id,
                "name": "Assistant",
                "config": {},
                "metadata": {},
            }
    
    async def search_assistants(self, graph_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """Search for assistants by graph ID."""
        try:
            return await self.client.assistants.search(graph_id=graph_id, limit=limit)
        except Exception as e:
            return []
    
    async def get_threads(self, assistant_id: Optional[str] = None, limit: int = 20) -> list[dict[str, Any]]:
        """Get threads for an assistant."""
        try:
            params = {}
            if assistant_id:
                params["assistant_id"] = assistant_id
            return await self.client.threads.search(limit=limit, **params)
        except Exception as e:
            return []
    
    async def create_thread(self) -> dict[str, Any]:
        """Create a new thread."""
        return await self.client.threads.create()
    
    async def delete_thread(self, thread_id: str) -> None:
        """Delete a thread."""
        await self.client.threads.delete(thread_id)
    
    async def get_thread_state(self, thread_id: str) -> dict[str, Any]:
        """Get state for a thread."""
        return await self.client.threads.get_state(thread_id)
    
    async def update_thread_state(self, thread_id: str, values: dict[str, Any]) -> dict[str, Any]:
        """Update state for a thread."""
        return await self.client.threads.update_state(thread_id, values=values)
    
    async def stream_thread(
        self,
        thread_id: str,
        assistant_id: str,
        input_data: Optional[dict[str, Any]] = None,
        config: Optional[dict[str, Any]] = None,
        checkpoint: Optional[dict[str, Any]] = None,
        interrupt_before: Optional[list[str]] = None,
        interrupt_after: Optional[list[str]] = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream events from a thread execution."""
        stream_params = {
            "thread_id": thread_id,
            "assistant_id": assistant_id,
            "input": input_data or {},
            "config": config or {},
            "stream_mode": ["messages", "values", "updates"],
        }
        
        if checkpoint:
            stream_params["checkpoint"] = checkpoint
        
        if interrupt_before:
            stream_params["interrupt_before"] = interrupt_before
        
        if interrupt_after:
            stream_params["interrupt_after"] = interrupt_after
        
        # Use the async generator directly instead of async with
        print(f"🔄 Starting stream for thread {thread_id} with params: {stream_params}")
        try:
            # Get the stream object
            stream = self.client.runs.stream(**stream_params)
            event_count = 0
            
            # Iterate through the stream asynchronously
            async for event in stream:
                event_count += 1
                
                # StreamPart object has attributes: event, data, ns, run_id, etc.
                event_type = getattr(event, 'event', 'unknown')
                event_data = getattr(event, 'data', event)
                
                print(f"📩 Stream event #{event_count}: {event_type}")
                print(f"   Data type: {type(event_data).__name__}")
                print(f"   Data: {str(event_data)[:500]}")
                
                # Yield the event in a format the UI expects
                yield {
                    "event": event_type,
                    "data": event_data,
                }
            
            print(f"✅ Stream completed with {event_count} events")
        except Exception as e:
            print(f"❌ Stream error: {e}")
            import traceback
            traceback.print_exc()
            yield {"event": "error", "data": {"error": str(e)}}
    
    async def submit_run(
        self,
        thread_id: str,
        assistant_id: str,
        input_data: Optional[dict[str, Any]] = None,
        config: Optional[dict[str, Any]] = None,
        checkpoint: Optional[dict[str, Any]] = None,
        interrupt_before: Optional[list[str]] = None,
        interrupt_after: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Submit a run to a thread."""
        params = {
            "thread_id": thread_id,
            "assistant_id": assistant_id,
            "input": input_data or {},
            "config": config or {},
        }
        
        if checkpoint:
            params["checkpoint"] = checkpoint
        
        if interrupt_before:
            params["interrupt_before"] = interrupt_before
        
        if interrupt_after:
            params["interrupt_after"] = interrupt_after
        
        return await self.client.runs.create(**params)
