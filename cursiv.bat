@echo off
:: Cursiv terminal command — place this file (or its folder) on your PATH.
:: Usage: cursiv            (opens chat in current folder)
::        cursiv --help
cd /d "%~dp0"
if exist "%~dp0secrets.bat" call "%~dp0secrets.bat"
python -m cursiv_v215.ui.chat_cli %*
