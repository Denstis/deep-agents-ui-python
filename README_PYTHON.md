# Deep Agents UI - Python Version with LM Studio Support

A Python-based reimplementation of the [Deep Agents UI](https://github.com/langchain-ai/deep-agents-ui) using FastAPI, designed to work with LangGraph deployments and local LM Studio instances.

## Features

- 🚀 **FastAPI Backend**: Modern async Python web framework
- 💬 **Real-time Streaming**: Server-Sent Events (SSE) for streaming responses
- 🧵 **Thread Management**: Create, manage, and switch between conversation threads
- ⚙️ **LM Studio Integration**: Direct integration with local LM Studio instances
- 🎨 **Dark Theme UI**: Clean, modern interface similar to the original
- 🔌 **LangGraph SDK**: Full support for LangGraph agent deployments

## Installation

### Prerequisites

- Python 3.10+
- Node.js and yarn (for original UI reference)
- LM Studio (optional, for local LLM inference)
- LangGraph deployment (optional, for agent workflows)

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Start the Application

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Open in Browser

Navigate to `http://localhost:8000`

### 3. Configure Your Deployment

Click the Settings button and enter:
- **Deployment URL**: Your LangGraph deployment URL (e.g., `http://127.0.0.1:2024`)
- **Assistant ID**: Your assistant/graph ID (e.g., `research`)
- **LangSmith API Key** (optional): For accessing deployed applications

## LM Studio Integration

To use with local LM Studio:

### 1. Start LM Studio

1. Download and install [LM Studio](https://lmstudio.ai/)
2. Load a model
3. Start the local server (default: `http://localhost:1234`)

### 2. Set Environment Variable

```bash
export LMSTUDIO_URL="http://localhost:1234"
```

Or create a `.env` file:

```env
LMSTUDIO_URL=http://localhost:1234
```

### 3. Use Direct Chat Endpoint

The application provides direct LM Studio endpoints:

- `POST /api/lmstudio/chat` - Standard chat completion
- `POST /api/lmstudio/chat/stream` - Streaming chat completion

Example usage:

```bash
curl -X POST http://localhost:8000/api/lmstudio/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "temperature": 0.7
  }'
```

## API Reference

### Configuration Endpoints

- `GET /api/config` - Get current configuration
- `POST /api/config` - Save configuration

### Thread Endpoints

- `GET /api/threads` - List all threads
- `POST /api/threads` - Create new thread
- `DELETE /api/threads/{thread_id}` - Delete a thread
- `GET /api/threads/{thread_id}/state` - Get thread state
- `POST /api/threads/{thread_id}/state` - Update thread state

### Streaming Endpoints

- `POST /api/stream` - Stream agent execution with SSE
- `POST /api/runs` - Create run without streaming

### LM Studio Endpoints

- `POST /api/lmstudio/chat` - Direct chat with LM Studio
- `POST /api/lmstudio/chat/stream` - Streaming chat with LM Studio

### WebSocket

- `WS /ws/{session_id}` - Real-time bidirectional communication

## Project Structure

```
/workspace
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── app/
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   └── langgraph_client.py # LangGraph client wrapper
├── templates/
│   └── index.html         # Main HTML UI
└── static/                # Static files (CSS, JS, images)
```

## Comparison with Original

| Feature | Original (Next.js) | Python Version |
|---------|-------------------|----------------|
| Framework | Next.js/React | FastAPI + Vanilla JS |
| Language | TypeScript | Python |
| State Management | React Context/useState | Session cookies |
| Streaming | langgraph-sdk/react | SSE (sse-starlette) |
| UI Components | Radix UI | Custom CSS |
| Bundle Size | ~50MB (node_modules) | ~5MB |

## Usage with LangGraph

This UI is designed to work with LangGraph deployments. To set up a LangGraph deployment:

```bash
# Clone deepagents examples
git clone https://github.com/langchain-ai/deepagents.git
cd deepagents/examples/deep_research

# Install dependencies
pip install -r requirements.txt

# Start LangGraph dev server
langgraph dev
```

Then configure the UI with:
- Deployment URL: `http://127.0.0.1:2024`
- Assistant ID: `research` (or your graph name from `langgraph.json`)

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LMSTUDIO_URL` | LM Studio server URL | `http://localhost:1234` |
| `LANGSMITH_API_KEY` | LangSmith API key | None |

## Development

### Running in Development Mode

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
```

### Adding New Features

1. Add API endpoints in `main.py`
2. Update the frontend in `templates/index.html`
3. Add any shared logic in the `app/` directory

## License

MIT License - based on the original [Deep Agents UI](https://github.com/langchain-ai/deep-agents-ui)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
