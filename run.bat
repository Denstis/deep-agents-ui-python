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
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:1234/v1/models' -TimeoutSec 3 -ErrorAction Stop; Write-Host '[OK] LM Studio is running on http://localhost:1234' } catch { Write-Host '[WARNING] LM Studio is NOT running on http://localhost:1234' -ForegroundColor Yellow; Write-Host 'Please start LM Studio and load a model first!' }"
echo.

REM Start LangGraph local server in a separate window
echo [6/6] Starting LangGraph local server...
where langgraph >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] langgraph-cli detected. Starting LangGraph dev server on port 6000...
    echo.
    REM Start in new window with proper path activation
    start "LangGraph Server" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && langgraph dev --port 6000 --host 127.0.0.1 --no-browser"
    
    echo [WAIT] Waiting for LangGraph to initialize on port 6000...
    
    REM Wait for port 6000 to be available (up to 30 seconds)
    set /a max_attempts=15
    set /a attempt=0
    :wait_loop
    set /a attempt+=1
    timeout /t 2 /nobreak >nul
    powershell -Command "$tcp = New-Object Net.Sockets.TcpClient; try { $tcp.Connect('127.0.0.1', 6000); if($tcp.Connected) { exit 0 } else { exit 1 } } catch { exit 1 }"
    if %errorlevel% equ 0 (
        echo [OK] LangGraph is ready on http://127.0.0.1:6000
        goto :langgraph_ready
    )
    if %attempt% geq %max_attempts% (
        echo [WARN] LangGraph startup timeout after %attempt% attempts.
        echo Check the LangGraph Server window for errors.
        goto :langgraph_ready
    )
    goto :wait_loop
    
    :langgraph_ready
) else (
    echo [ERROR] langgraph command not found even after installation.
    echo Please check the installation logs above.
    echo The app will start but you may need to use a cloud LangGraph deployment.
    timeout /t 3 >nul
)
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
echo (The LangGraph server window will remain open - close it separately)
echo ============================================
echo.

REM Run the application
python main.py

pause
