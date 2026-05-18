@echo off
REM Cursiv v3.0 - Clean Launcher (no black console window)
REM This batch file starts the launcher using pythonw to hide the console

setlocal
cd /d "%~dp0"

REM Try to use pythonw first (recommended - no console)
where pythonw >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    start "" pythonw hide_console.pyw
) else (
    REM Fallback to python if pythonw not found
    start "" pythonw main.py
)

endlocal
exit