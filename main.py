"""FastAPI application for Deep Agents UI with LM Studio support."""

import os
import uuid
import json
from pathlib import Path
from typing import Optional, Any, AsyncGenerator
from contextlib import asynccontextmanager

# Ensure required directories exist
Path("static").mkdir(exist_ok=True)
Path("templates").mkdir(exist_ok=True)

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
import httpx

from app.config import StandaloneConfig, get_config, save_config
from app.langgraph_client import LangGraphClientWrapper


# ============== Pydantic Models ==============

class ConfigRequest(BaseModel):
    """Request model for configuration."""
    deployment_url: str = Field(..., description="LangGraph deployment URL")
    assistant_id: str = Field(..., description="Assistant ID")
    langsmith_api_key: Optional[str] = Field(None, description="Optional LangSmith API key")


class MessageRequest(BaseModel):
    """Request model for sending a message."""
    message: str = Field(..., description="The message content")
    thread_id: Optional[str] = Field(None, description="Thread ID (creates new if not provided)")


class StreamRequest(BaseModel):
    """Request model for streaming."""
    thread_id: str
    message: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    checkpoint: Optional[dict[str, Any]] = None
    interrupt_before: Optional[list[str]] = None
    interrupt_after: Optional[list[str]] = None


class StateUpdateRequest(BaseModel):
    """Request model for updating thread state."""
    values: dict[str, Any]


# ============== Application State ==============

class AppState:
    """Application state management."""
    
    def __init__(self):
        self.clients: dict[str, LangGraphClientWrapper] = {}
        self.threads: dict[str, dict[str, Any]] = {}  # session_id -> thread info
    
    def get_or_create_client(self, session_id: str, config: StandaloneConfig) -> LangGraphClientWrapper:
        """Get or create a LangGraph client for a session."""
        if session_id not in self.clients:
            self.clients[session_id] = LangGraphClientWrapper(
                deployment_url=config.deployment_url,
                api_key=config.langsmith_api_key,
            )
        return self.clients[session_id]


app_state = AppState()


# ============== FastAPI App ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("🚀 Deep Agents UI (Python + LM Studio) starting...")
    yield
    # Shutdown
    print("👋 Shutting down Deep Agents UI...")


app = FastAPI(
    title="Deep Agents UI",
    description="Python-based UI for Deep Agents with LM Studio support",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# ============== API Routes ==============

@app.get("/")
async def root():
    """Serve the main HTML page."""
    with open("templates/index.html", "r") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/config")
async def get_configuration(request: Request):
    """Get current configuration."""
    session_id = request.cookies.get("session_id", str(uuid.uuid4()))
    config = get_config(session_id)
    if config:
        return {
            "deployment_url": config.deployment_url,
            "assistant_id": config.assistant_id,
            "has_api_key": bool(config.langsmith_api_key),
        }
    return {"configured": False}


@app.post("/api/config")
async def save_configuration(request: Request, config_req: ConfigRequest):
    """Save configuration."""
    session_id = request.cookies.get("session_id", str(uuid.uuid4()))
    config = StandaloneConfig(
        deployment_url=config_req.deployment_url,
        assistant_id=config_req.assistant_id,
        langsmith_api_key=config_req.langsmith_api_key,
    )
    save_config(session_id, config)
    
    # Initialize client
    app_state.get_or_create_client(session_id, config)
    
    response = JSONResponse(content={"status": "ok"})
    response.set_cookie("session_id", session_id, max_age=86400 * 7)  # 7 days
    return response


@app.get("/api/assistant")
async def get_assistant(request: Request):
    """Get assistant information."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="No session configured")
    
    config = get_config(session_id)
    if not config:
        raise HTTPException(status_code=400, detail="No configuration found")
    
    client = app_state.get_or_create_client(session_id, config)
    assistant = await client.get_assistant(config.assistant_id)
    return assistant


@app.get("/api/threads")
async def list_threads(request: Request, limit: int = 20):
    """List threads for the current assistant."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="No session configured")
    
    config = get_config(session_id)
    if not config:
        raise HTTPException(status_code=400, detail="No configuration found")
    
    client = app_state.get_or_create_client(session_id, config)
    threads = await client.get_threads(assistant_id=config.assistant_id, limit=limit)
    return {"threads": threads}


@app.post("/api/threads")
async def create_thread(request: Request):
    """Create a new thread."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="No session configured")
    
    config = get_config(session_id)
    if not config:
        raise HTTPException(status_code=400, detail="No configuration found")
    
    client = app_state.get_or_create_client(session_id, config)
    thread = await client.create_thread()
    return thread


@app.delete("/api/threads/{thread_id}")
async def delete_thread(request: Request, thread_id: str):
    """Delete a thread."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="No session configured")
    
    config = get_config(session_id)
    if not config:
        raise HTTPException(status_code=400, detail="No configuration found")
    
    client = app_state.get_or_create_client(session_id, config)
    await client.delete_thread(thread_id)
    return {"status": "deleted"}


@app.get("/api/threads/{thread_id}/state")
async def get_thread_state(request: Request, thread_id: str):
    """Get state for a thread."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="No session configured")
    
    config = get_config(session_id)
    if not config:
        raise HTTPException(status_code=400, detail="No configuration found")
    
    client = app_state.get_or_create_client(session_id, config)
    state = await client.get_thread_state(thread_id)
    return state


@app.post("/api/threads/{thread_id}/state")
async def update_thread_state(
    request: Request,
    thread_id: str,
    state_update: StateUpdateRequest,
):
    """Update state for a thread."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="No session configured")
    
    config = get_config(session_id)
    if not config:
        raise HTTPException(status_code=400, detail="No configuration found")
    
    client = app_state.get_or_create_client(session_id, config)
    state = await client.update_thread_state(thread_id, state_update.values)
    return state


@app.post("/api/stream")
async def stream_run(request: Request, stream_req: StreamRequest):
    """Stream a run execution."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="No session configured")
    
    config = get_config(session_id)
    if not config:
        raise HTTPException(status_code=400, detail="No configuration found")
    
    client = app_state.get_or_create_client(session_id, config)
    
    print(f"🚀 Starting stream for thread {stream_req.thread_id}, message: {stream_req.message[:50] if stream_req.message else 'None'}...")
    
    async def event_generator() -> AsyncGenerator[dict[str, Any], None]:
        try:
            async for event in client.stream_thread(
                thread_id=stream_req.thread_id,
                assistant_id=config.assistant_id,
                input_data={"messages": [{"type": "human", "content": stream_req.message}]} if stream_req.message else None,
                config=stream_req.config,
                checkpoint=stream_req.checkpoint,
                interrupt_before=stream_req.interrupt_before,
                interrupt_after=stream_req.interrupt_after,
            ):
                print(f"📤 Yielding event: {event.get('event', 'unknown')}")
                # Ensure data is properly serialized
                event_data = event.get("data", event)
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "event": event.get("event", "unknown"),
                        "data": event_data,
                    }, default=str),
                }
        except Exception as e:
            print(f"❌ Stream generator error: {e}")
            import traceback
            traceback.print_exc()
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}, default=str),
            }
    
    return EventSourceResponse(event_generator())


@app.post("/api/runs")
async def create_run(request: Request, stream_req: StreamRequest):
    """Create a run without streaming."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="No session configured")
    
    config = get_config(session_id)
    if not config:
        raise HTTPException(status_code=400, detail="No configuration found")
    
    client = app_state.get_or_create_client(session_id, config)
    run = await client.submit_run(
        thread_id=stream_req.thread_id,
        assistant_id=config.assistant_id,
        input_data={"messages": [{"type": "human", "content": stream_req.message}]} if stream_req.message else None,
        config=stream_req.config,
        checkpoint=stream_req.checkpoint,
        interrupt_before=stream_req.interrupt_before,
        interrupt_after=stream_req.interrupt_after,
    )
    return run


# ============== WebSocket Endpoint for Real-time Updates ==============

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    
    config = get_config(session_id)
    if not config:
        await websocket.send_json({"error": "No configuration found"})
        await websocket.close()
        return
    
    try:
        while True:
            data = await websocket.receive_json()
            # Handle WebSocket messages here
            # This can be used for real-time bidirectional communication
            await websocket.send_json({"status": "received", "data": data})
    except WebSocketDisconnect:
        pass


# ============== LM Studio Specific Endpoints ==============

class LMStudioMessage(BaseModel):
    """Message format for LM Studio."""
    role: str
    content: str


class LMStudioRequest(BaseModel):
    """Request format for LM Studio."""
    messages: list[LMStudioMessage]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False


@app.post("/api/lmstudio/chat")
async def lmstudio_chat(request: LMStudioRequest):
    """Direct chat with LM Studio (bypasses LangGraph)."""
    lmstudio_url = os.getenv("LMSTUDIO_URL", "http://localhost:1234")
    
    async with httpx.AsyncClient() as http_client:
        response = await http_client.post(
            f"{lmstudio_url}/v1/chat/completions",
            json=request.model_dump(),
            timeout=120.0,
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"LM Studio error: {response.text}",
            )
        
        return response.json()


@app.post("/api/lmstudio/chat/stream")
async def lmstudio_chat_stream(request: LMStudioRequest):
    """Streaming chat with LM Studio."""
    lmstudio_url = os.getenv("LMSTUDIO_URL", "http://localhost:1234")
    
    async def generate():
        async with httpx.AsyncClient() as http_client:
            async with http_client.stream(
                "POST",
                f"{lmstudio_url}/v1/chat/completions",
                json={**request.model_dump(), "stream": True},
                timeout=120.0,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        yield {"event": "message", "data": line[6:]}
    
    return EventSourceResponse(generate())


# ============== Main Entry Point ==============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
