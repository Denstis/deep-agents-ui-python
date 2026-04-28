@echo off
REM Deep Agents UI - Installation and Run Script for Windows
REM Requires Python 3.10+ installed

echo ============================================
echo   Deep Agents UI - Python + LM Studio
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/5] Checking Python version...
python --version

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [2/5] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
) else (
    echo [2/5] Virtual environment already exists
)

REM Activate virtual environment
echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

REM Install dependencies
echo [4/5] Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

REM Install LangGraph locally for standalone mode
echo.
echo [5/5] Setting up LangGraph local server...
echo Installing langgraph and langgraph-cli for local development...
pip install langgraph langgraph-cli langgraph-checkpoint-sqlite
if errorlevel 1 (
    echo WARNING: Failed to install langgraph packages, continuing with SDK-only mode...
)

REM Create required directories
if not exist "static" mkdir static
if not exist "templates" mkdir templates

echo.
echo ============================================
echo   Installation complete!
echo ============================================
echo.

REM Check if LM Studio is running
echo Checking LM Studio connection...
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:1234/v1/models' -TimeoutSec 3 -ErrorAction Stop; Write-Host '[OK] LM Studio is running on http://localhost:1234' } catch { Write-Host '[WARNING] LM Studio is NOT running on http://localhost:1234' -ForegroundColor Yellow; Write-Host 'Please start LM Studio and load a model first!' }"
echo.

REM Try to start local LangGraph if available
echo Checking LangGraph local server...
where langgraph >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] langgraph-cli detected. To run LangGraph locally:
    echo   langgraph dev --port 6000
    echo.
    echo Starting LangGraph local server in background...
    start "LangGraph Local" cmd /c "langgraph dev --port 6000"
    timeout /t 3 /nobreak >nul
) else (
    echo [INFO] langgraph-cli not installed. Using remote LangGraph deployment only.
    echo To enable local LangGraph, ensure you have a langgraph.json config file.
)
echo.

echo Starting Deep Agents UI server...
echo.
echo Open http://localhost:8000 in your browser
echo.
echo Configuration options:
echo   - LangGraph Deployment URL: http://localhost:6000 (local) or your cloud URL
echo   - LM Studio URL: http://localhost:1234 (default)
echo   - Set LMSTUDIO_URL env var to change LM Studio endpoint
echo.
echo Press Ctrl+C to stop the server
echo ============================================
echo.

REM Run the application
python main.py

pause
