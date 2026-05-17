@echo off
title JW Terminal Chat - JWFrontierEvoCore
cd /d "%~dp0"

REM Load API keys from secrets.bat (git-ignored)
if exist "%~dp0secrets.bat" (
    call "%~dp0secrets.bat"
) else (
    echo  [!] secrets.bat not found - you will need to enter keys manually.
)

REM Launch maximized terminal (inherits env vars set above)
start "JW Terminal Chat - JWFrontierEvoCore" /MAX /D "%~dp0" cmd /k "python -m cursiv_v215.ui.chat_cli & pause"
