@echo off
title Cursiv v3.0 - The Sovereign Temple
color 07
cd /d "%~dp0"

if exist "%~dp0secrets.bat" call "%~dp0secrets.bat"

echo.
echo  ========================================================
echo   CURSIV v3.0
echo   Sacred UI
echo  ========================================================
echo.
echo  Checking environment...

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found. Install Python 3.11+ first.
    pause
    exit /b 1
)

python -c "import streamlit" >nul 2>&1
if %errorlevel% neq 0 (
    echo  Installing Streamlit...
    python -m pip install "streamlit>=1.32.0" -q
)

python -c "import cursiv_v215" >nul 2>&1
if %errorlevel% neq 0 (
    python -m pip install -e . -q >nul 2>&1
)

echo  Starting the Sacred UI...
echo  Opening at: http://localhost:8501
echo.
echo  Press Ctrl+C to stop.
echo.

python -m streamlit run cursiv_v215/ui/app.py --server.port 8501 --server.headless false --browser.gatherUsageStats false

pause
