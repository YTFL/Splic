@echo off
rem ==============================================================================
rem SPLIC — Single-File Runner for Windows (Command Prompt / Double-Click)
rem Launches both the FastAPI backend and Next.js frontend concurrently.
rem ==============================================================================

setlocal enabledelayedexpansion

rem Determine repository root
set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"

cd /d "%ROOT_DIR%"

echo ==============================================================
echo           SPLIC -- Indic Video Auto-Editor Runner
echo ==============================================================
echo.

rem ------------------------------------------------------------------------------
rem 1. Dependency Checks: Node.js & npm
rem ------------------------------------------------------------------------------
echo [*] Checking Node.js and npm...
where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not found in PATH.
    echo Please install Node.js (v18+ or v20+ recommended) from https://nodejs.org/
    pause
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] npm is not found in PATH.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('node -v') do set "NODE_VER=%%v"
for /f "tokens=*" %%v in ('npm -v') do set "NPM_VER=%%v"
echo [OK] Node %NODE_VER% and npm %NPM_VER% detected.

rem ------------------------------------------------------------------------------
rem 2. Dependency Checks: Python
rem ------------------------------------------------------------------------------
echo [*] Checking Python environment...
set "VENV_DIR=%ROOT_DIR%\backend\.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    rem Detect system python
    set "SYSTEM_PY="
    where py >nul 2>nul
    if not errorlevel 1 (
        set "SYSTEM_PY=py -3"
    ) else (
        where python >nul 2>nul
        if not errorlevel 1 (
            set "SYSTEM_PY=python"
        )
    )

    if not defined SYSTEM_PY (
        echo [ERROR] Python 3 was not found in PATH.
        echo Please install Python 3.10+ from https://www.python.org/
        pause
        exit /b 1
    )

    echo [!] Python virtual environment not found in backend\.venv.
    echo [*] Creating virtual environment...
    %SYSTEM_PY% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )

    echo [*] Installing backend dependencies from requirements.txt...
    "%VENV_PYTHON%" -m pip install --upgrade pip
    "%VENV_DIR%\Scripts\pip.exe" install -r "%ROOT_DIR%\backend\requirements.txt"
    if errorlevel 1 (
        echo [WARNING] Some dependencies failed to install. Continuing...
    ) else (
        echo [OK] Backend virtual environment created and configured.
    )
) else (
    echo [OK] Existing virtual environment found: %VENV_DIR%
)

rem ------------------------------------------------------------------------------
rem 3. Environment Files Setup
rem ------------------------------------------------------------------------------
echo [*] Verifying environment files...

rem Backend .env
if not exist "%ROOT_DIR%\backend\.env" (
    if exist "%ROOT_DIR%\backend\.env.example" (
        echo [!] backend\.env missing. Creating from .env.example (add your SARVAM_API_KEY)...
        copy "%ROOT_DIR%\backend\.env.example" "%ROOT_DIR%\backend\.env" >nul
    )
)

rem Frontend .env.local
if exist "%ROOT_DIR%\.env.local" (
    if not exist "%ROOT_DIR%\timeline_studio\.env.local" (
        echo [*] Copying root .env.local into timeline_studio\...
        copy "%ROOT_DIR%\.env.local" "%ROOT_DIR%\timeline_studio\.env.local" >nul
    )
)

rem ------------------------------------------------------------------------------
rem 4. Frontend Dependencies Check
rem ------------------------------------------------------------------------------
if not exist "%ROOT_DIR%\timeline_studio\node_modules" (
    echo [!] timeline_studio\node_modules missing. Running npm install...
    cd /d "%ROOT_DIR%\timeline_studio"
    call npm install
    cd /d "%ROOT_DIR%"
    echo [OK] Frontend dependencies installed.
)

rem ------------------------------------------------------------------------------
rem 5. Launch Servers Concurrently
rem ------------------------------------------------------------------------------
echo.
echo ==============================================================
echo   All systems ready! Launching Backend & Frontend...
echo ==============================================================
echo   Frontend UI:  http://localhost:3000
echo   Backend API:  http://localhost:8000
echo   API Docs:     http://localhost:8000/docs
echo ==============================================================
echo   Backend will run in a separate window.
echo   Frontend will stream in this window.
echo   Press Ctrl+C to stop frontend. Close the backend window to stop backend.
echo ==============================================================
echo.

rem Launch backend in a dedicated titled window
start "Splic - Backend (FastAPI)" cmd /k "title Splic - Backend (FastAPI) && cd /d "%ROOT_DIR%\backend" && call "%VENV_DIR%\Scripts\activate.bat" && python -m uvicorn main:app --reload --port 8000"

rem Launch frontend in the current window
cd /d "%ROOT_DIR%\timeline_studio"
title Splic - Frontend (Next.js)
call npm run dev

rem When frontend exits, prompt user
echo.
echo Frontend stopped. You can close the Backend window if you're done.
pause

