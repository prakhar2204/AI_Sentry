@echo off
cd /d "%~dp0app\frontend"
set "SENTRYPHI_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%SENTRYPHI_PYTHON%" (
  echo Project Python environment is missing.
  exit /b 1
)
set "SENTRYPHI_USE_BUILD=1"
set "ELECTRON_RUN_AS_NODE="
call npm run build
if errorlevel 1 exit /b 1
call node_modules\.bin\electron.cmd .
