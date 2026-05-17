@echo off
title JW Main Chat - Cursiv v3.0
color 07
cd /d "%~dp0"

if exist "%~dp0secrets.bat" call "%~dp0secrets.bat"

:: Quick dep check
python -c "import gradio" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] gradio not found -- installing...
    python -m pip install "gradio>=4.44.0" -q
    python -m pip install -e . -q >nul 2>&1
)

echo.
echo  ========================================================
echo   JW MAIN CHAT - Cursiv v3.0
echo   Cursiv v3.0  ^|  http://localhost:7860
echo  ========================================================
echo.
echo  Starting main chat interface...
echo  Open your browser at: http://localhost:7860
echo.

python -m cursiv_v215.ui.chat_app
pause
