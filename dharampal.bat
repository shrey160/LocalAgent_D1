@echo off
setlocal
cd /d "%~dp0"

if "%~1"=="start" (
    call venv\Scripts\activate.bat
    python -m dharampal.cli start
) else if "%~1"=="stop" (
    call venv\Scripts\activate.bat
    python -m dharampal.cli stop
) else (
    echo Usage: dharampal start ^| stop
)
