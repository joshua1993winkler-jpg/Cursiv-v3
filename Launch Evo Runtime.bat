@echo off
title Cursiv v3.0 — Evolutionary Runtime
color 0A

if exist secrets.bat call secrets.bat

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   Cursiv v3.0  —  Evolutionary Runtime   ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Self-heal deps
python -c "import cursiv_v215.runtime.db" 2>nul || (
    echo  Installing cursiv_v215 package...
    pip install -e . -q
)
python -c "import numpy" 2>nul || pip install numpy -q
python -c "import sklearn" 2>nul || pip install scikit-learn -q

echo  Select an action:
echo.
echo  [1] Run cycle now
echo  [2] Check status
echo  [3] List pending deltas
echo  [4] Approve all pending deltas
echo  [5] Run prune (dry run)
echo  [6] List top wisdom
echo  [7] Start scheduler (background loop)
echo  [8] Exit
echo.
set /p choice=" > "

if "%choice%"=="1" (
    python -m cursiv_v215.cli.evo_cli run-cycle
    goto end
)
if "%choice%"=="2" (
    python -m cursiv_v215.cli.evo_cli status
    goto end
)
if "%choice%"=="3" (
    python -m cursiv_v215.cli.evo_cli list-deltas
    goto end
)
if "%choice%"=="4" (
    python -m cursiv_v215.cli.evo_cli approve-all
    goto end
)
if "%choice%"=="5" (
    python -m cursiv_v215.cli.evo_cli prune --dry-run
    goto end
)
if "%choice%"=="6" (
    python -m cursiv_v215.cli.evo_cli wisdom --limit 20
    goto end
)
if "%choice%"=="7" (
    echo Starting background scheduler (Ctrl+C to stop)...
    python -c "from cursiv_v215.runtime.scheduler import start; import time; start(); [time.sleep(60) for _ in iter(int, 1)]"
    goto end
)
if "%choice%"=="8" exit /b

:end
echo.
pause
