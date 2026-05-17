@echo off
title PiForge Vault Seeder - Cursiv v2.1.5
color 07
cd /d "%~dp0"

if exist "%~dp0secrets.bat" call "%~dp0secrets.bat"

echo.
echo  ================================================================
echo   PIFORGE VAULT SEEDER - Cursiv v2.1.5
echo   Reads 280 JSON packets (14 phases x 20) and seeds the vault
echo   with 14 fully-populated PiForge phase agents.
echo  ================================================================
echo.
echo  PiForge source: C:\Users\joshu\OneDrive\Desktop\Winkler_PiForge_AI
echo.

python piforge_importer.py %*

echo.
pause
