#!/bin/bash
# Deep Agents UI - Installation and Run Script for Linux/Mac
# Requires Python 3.10+ installed

echo "============================================"
echo "  Deep Agents UI - Python + LM Studio"
echo "============================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python is not installed or not in PATH"
    echo "Please install Python 3.10+"
    exit 1
fi

echo "[1/6] Checking Python version..."
python3 --version

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "[2/6] Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment"
        exit 1
    fi
else
    echo "[2/6] Virtual environment already exists"
fi

# Activate virtual environment
echo "[3/6] Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to activate virtual environment"
    exit 1
fi

# Install dependencies
echo "[4/6] Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi

# Install LangGraph locally for standalone mode
echo ""
echo "[5/6] Setting up LangGraph local server..."
echo "Installing langgraph-cli for local development..."
pip install langgraph-cli "langgraph-cli[inmem]" langgraph-checkpoint-sqlite
if [ $? -ne 0 ]; then
    echo "WARNING: Failed to install langgraph packages, continuing with SDK-only mode..."
fi

# Create required directories
mkdir -p static templates

echo ""
echo "============================================"
echo "  Installation complete!"
echo "============================================"
echo ""

# Check if LM Studio is running
echo "Checking LM Studio connection..."
if curl -s --connect-timeout 3 http://localhost:1234/v1/models > /dev/null 2>&1; then
    echo "[OK] LM Studio is running on http://localhost:1234"
else
    echo "[WARNING] LM Studio is NOT running on http://localhost:1234"
    echo "Please start LM Studio and load a model first!"
fi
echo ""

# Start LangGraph local server in background
echo "[6/6] Starting LangGraph local server..."
if command -v langgraph &> /dev/null; then
    echo "[INFO] langgraph-cli detected. Starting LangGraph dev server on port 6000..."
    echo ""
    
    # Start in background and redirect output to log
    langgraph dev --port 6000 --host 127.0.0.1 --no-browser > langgraph.log 2>&1 &
    LANGGRAPH_PID=$!
    echo "[INFO] LangGraph server started with PID $LANGGRAPH_PID"
    
    echo "[WAIT] Waiting for LangGraph to initialize on port 6000..."
    
    # Wait for port 6000 to be available (up to 30 seconds)
    max_attempts=15
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        attempt=$((attempt + 1))
        sleep 2
        if curl -s --connect-timeout 2 http://127.0.0.1:6000/docs > /dev/null 2>&1; then
            echo "[OK] LangGraph is ready on http://127.0.0.1:6000"
            break
        fi
        if [ $attempt -ge $max_attempts ]; then
            echo "[WARN] LangGraph startup timeout after $attempt attempts."
            echo "Check langgraph.log file for errors."
            break
        fi
    done
else
    echo "[ERROR] langgraph command not found even after installation."
    echo "Please check the installation logs above."
    echo "The app will start but you may need to use a cloud LangGraph deployment."
    sleep 3
fi
echo ""

echo "Starting Deep Agents UI server..."
echo ""
echo "Open http://localhost:8000 in your browser"
echo ""
echo "Default Configuration:"
echo "  - LangGraph URL: http://localhost:6000"
echo "  - LM Studio URL: http://localhost:1234"
echo ""
echo "Press Ctrl+C to stop the UI server."
echo "(The LangGraph server will remain running in background)"
echo "============================================"
echo ""

# Run the application
python main.py
