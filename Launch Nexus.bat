@echo off
title JW Command Nexus - Cursiv-v2.1.5
color 07
cd /d "%~dp0"

echo.
echo  ========================================================
echo   JW COMMAND NEXUS - JWFrontierEvoCore v1.0
echo   Cursiv-v2.1.5  ^|  http://localhost:7861
echo  ========================================================
echo.
echo  Starting Nexus panel...
echo  Open your browser at: http://localhost:7861
echo.

python -m cursiv_v215.ui.nexus_app
pause
