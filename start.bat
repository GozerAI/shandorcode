@echo off
REM ShandorCode - Quick Start Script for Windows

echo.
echo ========================================
echo   ShandorCode - Code Visualization
echo ========================================
echo.

REM Set UTF-8 encoding
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

REM Check if running from correct directory
if not exist "src\api\server.py" (
    echo ERROR: Must run from shandorcode project root!
    echo Current directory: %CD%
    pause
    exit /b 1
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.12+
    pause
    exit /b 1
)

echo Starting ShandorCode server on port 8765...
echo.
echo Open your browser to: http://localhost:8765
echo.
echo Press CTRL+C to stop the server
echo.

REM Start server with current directory as analysis path
python -m src.api.server --path "%CD%"
