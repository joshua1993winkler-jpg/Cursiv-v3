@echo off
title JW Main Chat - JWFrontierEvoCore
color 07
cd /d "%~dp0"

if exist "%~dp0secrets.bat" call "%~dp0secrets.bat"

echo.
echo  ========================================================
echo   JW MAIN CHAT - JWFrontierEvoCore v1.0
echo   Cursiv-v2.1.5  ^|  http://localhost:7860
echo  ========================================================
echo.
echo  Starting main chat interface...
echo  Open your browser at: http://localhost:7860
echo.

python -m cursiv_v215.ui.chat_app
pause
