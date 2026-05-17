@echo off
setlocal enabledelayedexpansion
title Cursiv v3.0 -- Setup & Launch
color 07
cls
cd /d "%~dp0"

echo.
echo  +-----------------------------------------------+
echo  ^|     CURSIV v3.0 -- SETUP ^& LAUNCH            ^|
echo  ^|     Cursiv v3.0  ^|  Full Stack                 ^|
echo  +-----------------------------------------------+
echo.

:: -- Load API keys if present ---------------------------------------------------
if exist "%~dp0secrets.bat" (
    call "%~dp0secrets.bat"
    echo  [OK] secrets.bat loaded
) else (
    echo  [INFO] secrets.bat not found -- enter keys manually in the UI
)
echo.

:: -- Check Python ---------------------------------------------------------------
echo  [1/5] Checking Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found.
    echo.
    echo  Install Python 3.11+ from https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  [OK] %PYVER%

:: -- Check pip ------------------------------------------------------------------
echo  [2/5] Checking pip...
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] pip not found. Reinstall Python with pip included.
    pause
    exit /b 1
)
python -m pip install --upgrade pip -q
echo  [OK] pip up to date

:: -- Install all requirements ---------------------------------------------------
echo  [3/5] Installing requirements...
echo.

echo  Installing from requirements.txt...
python -m pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo  [ERROR] requirements.txt install failed.
    echo  Check your internet connection and try again.
    pause
    exit /b 1
)
echo  [OK] gradio, streamlit, prompt_toolkit installed

:: -- Register the package -------------------------------------------------------
echo  [4/5] Registering cursiv_v215 package...
python -m pip install -e . -q >nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] Package registered ^(cursiv_v215 importable system-wide^)
) else (
    echo  [INFO] Editable install skipped -- app will still work
)

:: -- Optional services ----------------------------------------------------------
echo  [5/5] Checking optional services...
where ollama >nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] Ollama found -- local inference available
) else (
    echo  [INFO] Ollama not installed -- install from https://ollama.com for offline mode
)
if defined XAI_API_KEY       (echo  [OK] XAI_API_KEY set) else (echo  [INFO] XAI_API_KEY not set)
if defined OPENAI_API_KEY    (echo  [OK] OPENAI_API_KEY set) else (echo  [INFO] OPENAI_API_KEY not set)
if defined ANTHROPIC_API_KEY (echo  [OK] ANTHROPIC_API_KEY set) else (echo  [INFO] ANTHROPIC_API_KEY not set)

:: -- Done -----------------------------------------------------------------------
echo.
echo  ================================================
echo   Setup complete.
echo.
echo   To launch everything:  START CURSIV SYSTEM.bat
echo   Terminal chat only:    Launch Chat CLI.bat
echo   Web UI only:           Launch Chat.bat
echo   Nexus panel only:      Launch Nexus.bat
echo  ================================================
echo.
pause
