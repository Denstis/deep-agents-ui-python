@echo off
setlocal EnableDelayedExpansion
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

echo [1/6] Checking Python version...
python --version

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [2/6] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
) else (
    echo [2/6] Virtual environment already exists
)

REM Activate virtual environment
echo [3/6] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

REM Install dependencies
echo [4/6] Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

REM Install LangGraph locally for standalone mode
echo.
echo [5/6] Setting up LangGraph local server...
echo Installing langgraph-cli for local development...
pip install langgraph-cli "langgraph-cli[inmem]" langgraph-checkpoint-sqlite
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
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:1234/v1/models' -TimeoutSec 3 -ErrorAction Stop; Write-Host '[OK] LM Studio is running' } catch { Write-Host '[WARNING] LM Studio not detected' }"
echo.

REM Start LangGraph local server in a separate window
echo [6/6] Starting LangGraph local server...
where langgraph >nul 2>&1
set "LANGGRAPH_FOUND=%errorlevel%"

if "!LANGGRAPH_FOUND!" equ "0" (
    echo [INFO] langgraph-cli detected. Starting LangGraph dev server on port 6000...
    
    REM Start in new window - simplified and robust
    start "LangGraph Server" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && chcp 65001 >nul && langgraph dev --port 6000 --host 127.0.0.1 --no-browser"
    
    echo [WAIT] Waiting for LangGraph to initialize on port 6000...
    
    REM Wait for port 6000 with pure CMD (no PowerShell parsing issues)
    set /a max_attempts=15
    set /a attempt=0
    :wait_loop
    set /a attempt+=1
    timeout /t 2 /nobreak >nul
    netstat -ano | findstr /C:"127.0.0.1:6000" /C:"0.0.0.0:6000" /C:"*:6000" >nul
    if !errorlevel! equ 0 (
        echo [OK] LangGraph is ready on http://127.0.0.1:6000
        goto :langgraph_ready
    )
    if !attempt! geq !max_attempts! (
        echo [WARN] LangGraph startup timeout after !attempt! attempts.
        echo Check the LangGraph Server window for errors.
        goto :langgraph_ready
    )
    goto :wait_loop
) else (
    echo [WARN] langgraph-cli not found. Skipping local server start.
    echo You can use cloud LangGraph deployment instead.
)

:langgraph_ready
echo.
echo Starting Deep Agents UI server...
echo.
echo Open http://localhost:8000 in your browser
echo.
echo Default Configuration:
echo   - LangGraph URL: http://localhost:6000
echo   - LM Studio URL: http://localhost:1234
echo.
echo Press Ctrl+C to stop the UI server.
echo (Close the 'LangGraph Server' window separately to stop it)
echo ============================================
echo.

REM Run the application
python main.py

pause
