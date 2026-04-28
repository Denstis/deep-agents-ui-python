# Deep Agents UI - Python + LM Studio

A Python-based implementation of Deep Agents UI with local LangGraph support and LM Studio integration.

## Features

- 🚀 **Local LangGraph Server** - Run agents locally without cloud deployment
- 🤖 **LM Studio Integration** - Use local LLM models via LM Studio
- 💬 **Chat Interface** - Modern web UI for interacting with agents
- 🔧 **Easy Setup** - One-click installation and startup

## Prerequisites

1. **Python 3.10+** - [Download](https://www.python.org/downloads/)
2. **LM Studio** - [Download](https://lmstudio.ai/) (for local LLM inference)

## Quick Start (Windows)

```bash
run.bat
```

This will:
- Create a virtual environment
- Install all dependencies
- Start LangGraph local server on port 6000
- Start the UI server on port 8000

## Manual Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Start LangGraph local server
langgraph dev --port 6000 --host 127.0.0.1 --no-browser

# In another terminal, start the UI
python main.py
```

## Usage

1. Open http://localhost:8000 in your browser
2. Default configuration:
   - LangGraph URL: `http://127.0.0.1:6000`
   - Assistant ID: `agent`
3. Click "+ New Thread" to start chatting
4. Configure settings if needed

## Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
LANGGRAPH_URL=http://127.0.0.1:6000
LMSTUDIO_URL=http://localhost:1234
```

### Custom Agent

Edit `app/agent.py` to customize your agent's behavior. The default agent is a simple echo bot for testing.

## Project Structure

```
deep-agents-ui-python/
├── main.py                 # FastAPI application
├── run.bat                 # Windows installation script
├── requirements.txt        # Python dependencies
├── langgraph.json          # LangGraph configuration
├── app/
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   ├── langgraph_client.py # LangGraph SDK wrapper
│   └── agent.py            # Test agent definition
├── templates/
│   └── index.html          # Web UI
└── static/                 # Static assets
```

## API Endpoints

- `GET /` - Web UI
- `GET /api/config` - Get current configuration
- `POST /api/config` - Update configuration
- `GET /api/threads` - List threads
- `POST /api/threads` - Create new thread
- `POST /api/stream` - Stream messages to agent
- `GET /api/lmstudio/models` - List LM Studio models
- `POST /api/lmstudio/chat` - Chat with LM Studio directly

## Troubleshooting

### LangGraph not starting
- Ensure you have `langgraph-cli[inmem]` installed: `pip install -U "langgraph-cli[inmem]"`
- Check `langgraph.log` for errors
- Verify port 6000 is not in use

### LM Studio connection failed
- Make sure LM Studio is running
- Load a model in LM Studio
- Check that LM Studio server is enabled (default: http://localhost:1234)

### Browser issues
- Clear browser cache
- Try incognito/private mode
- Check browser console for errors

## License

MIT License
