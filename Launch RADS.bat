@echo off
title RADS -- Rogue Autonomous Defense System
color 0A
cd /d "%~dp0"

echo.
echo  =====================================================
echo   RADS -- Rogue Autonomous Defense System
echo   Cursiv Swarm Controller
echo  =====================================================
echo.

if exist "%~dp0secrets.bat" call "%~dp0secrets.bat"

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found.
    pause & exit /b 1
)

:: Install websockets if missing
python -c "import websockets" >nul 2>&1
if %errorlevel% neq 0 (
    echo  Installing websockets...
    python -m pip install websockets --quiet
)

echo.
echo  Modes:
echo    [1] LIVE    -- connect to ACEmulator plugin on localhost:9001
echo    [2] SIM     -- simulation mode, no ACE needed (test swarm logic)
echo    [3] STATUS  -- print threat memory and exit
echo.
set /p MODE="  Select mode [1/2/3]: "

if "%MODE%"=="2" (
    echo.
    echo  Starting in SIMULATION mode...
    python -m rads --sim
) else if "%MODE%"=="3" (
    python -m rads --status
    pause
) else (
    echo.
    echo  Starting in LIVE mode -- make sure ACEmulator is running with the RADS plugin.
    python -m rads
)

pause
