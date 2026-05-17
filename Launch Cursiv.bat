@echo off
title Cursiv v2.1.5 - The Sovereign Temple
color 07
cd /d "%~dp0"

echo.
echo  ========================================================
echo   CURSIV v2.1.5 - THE TEMPLE
echo   Black . Rose Gold . Lapis Eye
echo  ========================================================
echo.
echo  Checking environment...

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found. Install Python 3.11+ first.
    pause
    exit /b 1
)

where streamlit >nul 2>&1
if %errorlevel% neq 0 (
    echo  Installing Streamlit...
    pip install streamlit -q
)

echo  Starting the Sacred UI...
echo  Opening at: http://localhost:8501
echo.
echo  Press Ctrl+C to stop.
echo.

python -m streamlit run cursiv_v215/ui/app.py --server.port 8501 --server.headless false --browser.gatherUsageStats false

pause
