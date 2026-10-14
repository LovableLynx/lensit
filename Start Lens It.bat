@echo off
title Lens It
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo  Python is not installed.
  echo  1. Download Python 3.11 from https://www.python.org/downloads/
  echo  2. During install, tick "Add python.exe to PATH"
  echo  3. Double-click this file again
  echo.
  start "" https://www.python.org/downloads/
  pause
  exit /b
)
if not exist .venv (
  echo  First run: setting up Lens It. This needs internet once and takes a few minutes...
  python -m venv .venv || goto fail
  .venv\Scripts\pip install -q --require-hashes --only-binary=:all: -r requirements.txt || goto fail
  .venv\Scripts\python -c "from lensit.faces import download_models; download_models()" || goto fail
  echo  Setup complete. From now on Lens It works offline.
)
echo.
echo  Starting Lens It... your browser will open the setup screen.
echo  Keep this window open during the event. Close it to stop Lens It.
echo.
start "" cmd /c "timeout /t 10 >nul & start http://localhost:8000/setup"
.venv\Scripts\python -m lensit serve
pause
exit /b
:fail
echo.
echo  Setup failed. Check your internet connection and try again.
rmdir /s /q .venv 2>nul
pause
