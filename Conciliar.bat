@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist "src\pipeline\run_reconciliation.py" (
  echo No se encuentra el proyecto. Ejecute este archivo desde la carpeta reconciliation_engine.
  pause
  exit /b 1
)

set PYTHONPATH=%~dp0src

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0scripts\easy_run.py" %*
) else (
  python "%~dp0scripts\easy_run.py" %*
)

echo.
pause
