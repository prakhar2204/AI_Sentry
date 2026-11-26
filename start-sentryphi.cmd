@echo off
setlocal
cd /d "%~dp0app\frontend"
set "SENTRYPHI_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%SENTRYPHI_PYTHON%" (
  echo Project Python environment is missing.
  exit /b 1
)
set "SENTRYPHI_USE_BUILD="
set "ELECTRON_RUN_AS_NODE="
call npm.cmd run dev:electron
if errorlevel 1 pause
