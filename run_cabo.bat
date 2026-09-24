@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist "src\pipeline\run_reconciliation.py" (
  echo No se encuentra el proyecto. Ejecute este archivo desde la raiz del repositorio.
  exit /b 1
)

set PYTHONPATH=%~dp0src;%~dp0

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0scripts\cabo_runner.py" %*
) else (
  python "%~dp0scripts\cabo_runner.py" %*
)
exit /b %ERRORLEVEL%
