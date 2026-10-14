@echo off
title LocalLens
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
  echo  First run: setting up LocalLens. This needs internet once and takes a few minutes...
  python -m venv .venv || goto fail
  .venv\Scripts\pip install -q -r requirements.txt || goto fail
  .venv\Scripts\python -c "from locallens.faces import download_models; download_models()" || goto fail
  echo  Setup complete. From now on LocalLens works offline.
)
echo.
echo  Starting LocalLens... your browser will open the setup screen.
echo  Keep this window open during the event. Close it to stop LocalLens.
echo.
start "" cmd /c "timeout /t 10 >nul & start http://localhost:8000/setup"
.venv\Scripts\python -m locallens serve
pause
exit /b
:fail
echo.
echo  Setup failed. Check your internet connection and try again.
rmdir /s /q .venv 2>nul
pause
