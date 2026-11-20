@echo off
title AIHub server - keep this window open
cd /d "%~dp0"
call "..\.venv\Scripts\activate.bat"
set PYTHONPATH=src
set HF_HUB_OFFLINE=1
echo Starting AIHub... the page opens in about 10 seconds.
echo Close this window to stop the server.
start "" cmd /c "timeout /t 10 /nobreak >nul & start http://localhost:8000"
waitress-serve --listen=127.0.0.1:8000 --call aihub.api.app:app_factory
pause
