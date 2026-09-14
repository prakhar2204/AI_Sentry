@echo off
:: AI-SENTRY CLI launcher
:: Run from any directory. This script finds the backend folder relative to its own location.
set "BACKEND_DIR=%~dp0"
python "%BACKEND_DIR%__main__.py" %*
