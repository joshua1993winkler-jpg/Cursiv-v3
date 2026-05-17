@echo off
setlocal enabledelayedexpansion
title JWFrontierEvoCore -- Full System Boot
color 07
cd /d "%~dp0"

echo.
echo  ================================================================
echo   JWFrontierEvoCore v3.0
echo   FULL SYSTEM BOOT  ^|  Staggered Launcher
echo  ================================================================
echo.
echo   Components:
echo     [1] JW Main Chat          http://localhost:7860
echo     [2] JW Command Nexus      http://localhost:7861
echo     [3] Cursiv Sacred UI      http://localhost:8501
echo     [4] Terminal Chat CLI     (own maximized window)
echo     [5] Training Watcher      (background collector)
echo     [6] Ollama Inference      (if installed)
echo.
echo  ================================================================
echo.

:: ================================================================
::  PHASE 1 - LOAD SECRETS
:: ================================================================

if exist "%~dp0secrets.bat" (
    call "%~dp0secrets.bat"
    echo  [1/5] API keys loaded from secrets.bat
) else (
    echo  [1/5] secrets.bat not found -- enter keys manually in the UI
)
echo.

:: ================================================================
::  PHASE 2 - PYTHON CHECK
:: ================================================================

echo  [2/5] Checking Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Python not found. Install Python 3.10+ from:
    echo          https://python.org/downloads
    echo          Make sure to tick "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo         Python %PYVER%  OK
echo.

:: ================================================================
::  PHASE 3 - DEPENDENCIES  (fast check -- only installs if missing)
:: ================================================================

echo  [3/5] Checking dependencies...
python -c "import gradio, prompt_toolkit" >nul 2>&1
if %errorlevel% neq 0 (
    echo         Missing packages -- installing now (one-time)...
    python -m pip install --upgrade pip --quiet
    python -m pip install "gradio>=4.44.0" "prompt_toolkit>=3.0.0" --quiet
    python -m pip install -e . --quiet 2>nul
    echo         Install complete.
) else (
    python -c "import cursiv_v215" >nul 2>&1
    if %errorlevel% neq 0 (
        echo         Editable install missing -- registering package...
        python -m pip install -e . --quiet 2>nul
    ) else (
        echo         All packages present -- skipping install.
    )
)

:: Check Ollama
set OLLAMA_FOUND=0
where ollama >nul 2>&1
if %errorlevel% equ 0 (
    set OLLAMA_FOUND=1
    echo         Ollama detected -- local inference available.
)
echo.

:: ================================================================
::  PHASE 4 - PREP
:: ================================================================

if not exist ".cursiv" mkdir ".cursiv"
if not exist ".cursiv\vault" mkdir ".cursiv\vault"

:: ================================================================
::  PHASE 5 - STAGGERED LAUNCH
:: ================================================================

echo  [4/5] Booting components (staggered launch)...
echo.

:: -- [1/6] Main Chat (heaviest -- boot first, most time to settle)
echo   [1/6] JW Main Chat          port 7860 ...
start "JW Main Chat - 7860" cmd /k "cd /d "%~dp0" && if exist secrets.bat call secrets.bat && python -m cursiv_v215.ui.chat_app"
timeout /t 5 /nobreak >nul

:: -- [2/6] Command Nexus
echo   [2/6] JW Command Nexus      port 7861 ...
start "JW Command Nexus - 7861" cmd /k "cd /d "%~dp0" && if exist secrets.bat call secrets.bat && python -m cursiv_v215.ui.nexus_app"
timeout /t 4 /nobreak >nul

:: -- [3/6] Sacred UI (Streamlit)
echo   [3/6] Cursiv Sacred UI      port 8501 ...
start "Cursiv Sacred UI - 8501" cmd /k "cd /d "%~dp0" && if exist secrets.bat call secrets.bat && python -m streamlit run cursiv_v215/ui/app.py --server.port 8501 --server.headless false --browser.gatherUsageStats false"
timeout /t 4 /nobreak >nul

:: -- [4/6] Terminal Chat CLI (maximized standalone window)
echo   [4/6] Terminal Chat CLI     (maximized)...
start "JW Terminal Chat" /MAX cmd /k "cd /d "%~dp0" && if exist secrets.bat call secrets.bat && python -m cursiv_v215.ui.chat_cli"
timeout /t 2 /nobreak >nul

:: -- [5/6] Training Watcher
echo   [5/6] Training Watcher      (background)...
start "Training Watcher" cmd /k "cd /d "%~dp0" && python -m cursiv_v215.training.watcher"
timeout /t 2 /nobreak >nul

:: -- [6/6] Ollama (optional)
if %OLLAMA_FOUND% equ 1 (
    echo   [6/6] Ollama Mistral        (local inference)...
    start "Ollama - Mistral" cmd /k "ollama run mistral"
    timeout /t 2 /nobreak >nul
) else (
    echo   [6/6] Ollama                (not installed -- skip)
)
echo.

:: ================================================================
::  WAIT FOR SERVERS TO INITIALIZE
:: ================================================================

echo  [5/5] Waiting for servers to initialize...
echo.
echo        Main Chat binding port 7860...
timeout /t 4 /nobreak >nul
echo        Nexus binding port 7861...
timeout /t 3 /nobreak >nul
echo        Sacred UI binding port 8501...
timeout /t 3 /nobreak >nul
echo        All servers ready.
echo.

:: ================================================================
::  OPEN BROWSERS
:: ================================================================

echo  Opening browser tabs...
start "" "http://localhost:7860"
timeout /t 1 /nobreak >nul
start "" "http://localhost:7861"
timeout /t 1 /nobreak >nul
start "" "http://localhost:8501"
echo.

:: ================================================================
::  DONE
:: ================================================================

echo  ================================================================
echo.
echo   SYSTEM ONLINE
echo.
echo   JW Main Chat       http://localhost:7860     [LIVE]
echo   JW Command Nexus   http://localhost:7861     [LIVE]
echo   Cursiv Sacred UI   http://localhost:8501     [LIVE]
echo   Terminal Chat CLI  (own window, maximized)   [LIVE]
echo   Training Watcher   (background collector)    [LIVE]
if %OLLAMA_FOUND% equ 1 (
echo   Ollama Mistral     local inference           [LIVE]
)
echo.
echo  ================================================================
echo.
echo   HOW TO USE
echo   1. Keys auto-loaded from secrets.bat (all 3 APIs)
echo   2. Nexus  (7861)  -- repurpose agents, yin-yang balance
echo   3. Sacred (8501)  -- create and evolve agents
echo   4. Chat   (7860)  -- main Gradio interface with file tools
echo   5. CLI            -- paste-safe full-screen terminal chat
echo   6. Close any single window to stop just that component
echo.
echo   PiForge vault: 14 phase agents active in every conversation
echo.
echo  ================================================================
echo.
echo   Press any key to close this launcher window...
pause >nul
