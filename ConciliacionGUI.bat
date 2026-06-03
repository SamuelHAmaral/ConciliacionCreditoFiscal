@echo off
chcp 65001 >nul
title Conciliacion de credito fiscal
cd /d "%~dp0"
set PYTHONPATH=%~dp0;%~dp0src

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0desktop\conciliation_gui.py"
) else (
  python "%~dp0desktop\conciliation_gui.py"
)
if errorlevel 1 (
  echo.
  echo Si es la primera vez, instale dependencias:
  echo   py -3 -m pip install -r requirements.txt
  echo.
  pause
)
