@echo off
setlocal ENABLEDELAYEDEXPANSION
cd /d "%~dp0"

echo ============================================
echo   SourceBuild - Full Local Run (Frontend + Backend)
echo ============================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo [1/6] .venv not found. Creating virtual environment...
  where python >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    echo Please install Python 3.12+ and run again.
    pause
    exit /b 1
  )
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create .venv
    pause
    exit /b 1
  )
) else (
  echo [1/6] .venv found.
)

echo [2/6] Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
  echo [ERROR] Failed to upgrade pip
  pause
  exit /b 1
)

echo [3/6] Installing requirements...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] Failed to install requirements.txt
  pause
  exit /b 1
)

echo [4/6] Installing setuptools compatibility for mongomock fallback...
".venv\Scripts\python.exe" -m pip install "setuptools<81"
if errorlevel 1 (
  echo [ERROR] Failed to install compatible setuptools.
  pause
  exit /b 1
)

if not exist ".env" (
  if exist ".env.example" (
    echo [5/6] .env not found. Creating from .env.example...
    copy /Y ".env.example" ".env" >nul
  ) else (
    echo [5/6] .env and .env.example both missing. Please create .env manually.
  )
) else (
  echo [5/6] .env found.
)

if "%PORT%"=="" set PORT=5000
set FLASK_RUN_HOST=127.0.0.1
set FLASK_DEBUG=0

echo [6/6] Starting app on http://127.0.0.1:%PORT% ...
echo.
echo Frontend check:  http://127.0.0.1:%PORT%/
echo Backend health:  http://127.0.0.1:%PORT%/health
echo.
start "" "http://127.0.0.1:%PORT%/"
".venv\Scripts\python.exe" app.py

endlocal
