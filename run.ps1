# ==============================================================================
# SPLIC — Single-File Runner for Windows PowerShell
# Launches both the FastAPI backend and Next.js frontend concurrently.
# ==============================================================================

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$ROOT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT_DIR

Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host "          SPLIC -- Indic Video Auto-Editor Runner             " -ForegroundColor Cyan
Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host ""

# ------------------------------------------------------------------------------
# 1. Dependency Checks: Node.js & npm
# ------------------------------------------------------------------------------
Write-Host "[*] Checking Node.js and npm..." -ForegroundColor Blue
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Error "[ERROR] Node.js is not installed or not found in PATH. Please install from https://nodejs.org/"
    exit 1
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error "[ERROR] npm is not found in PATH."
    exit 1
}
$nodeVer = (node -v).Trim()
$npmVer = (npm -v).Trim()
Write-Host "[OK] Node $nodeVer and npm $npmVer detected." -ForegroundColor Green

# ------------------------------------------------------------------------------
# 2. Dependency Checks: Python & venv
# ------------------------------------------------------------------------------
Write-Host "[*] Checking Python environment..." -ForegroundColor Blue
$BACKEND_DIR = Join-Path $ROOT_DIR "backend"
$VENV_DIR = Join-Path $BACKEND_DIR ".venv"
$VENV_PYTHON = Join-Path $VENV_DIR "Scripts\python.exe"

if (-not (Test-Path $VENV_PYTHON)) {
    $systemPy = $null
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $systemPy = "py"
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $systemPy = "python"
    }

    if (-not $systemPy) {
        Write-Error "[ERROR] Python 3 was not found in PATH. Please install Python 3.10+ from https://www.python.org/"
        exit 1
    }

    Write-Host "[!] Virtual environment not found in backend\.venv. Creating..." -ForegroundColor Yellow
    if ($systemPy -eq "py") {
        & py -3 -m venv $VENV_DIR
    } else {
        & python -m venv $VENV_DIR
    }

    Write-Host "[*] Installing backend requirements..." -ForegroundColor Blue
    & $VENV_PYTHON -m pip install --upgrade pip
    & (Join-Path $VENV_DIR "Scripts\pip.exe") install -r (Join-Path $BACKEND_DIR "requirements.txt")
    Write-Host "[OK] Backend virtual environment created and configured." -ForegroundColor Green
} else {
    Write-Host "[OK] Existing virtual environment found: $VENV_DIR" -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# 3. Environment Files Setup
# ------------------------------------------------------------------------------
Write-Host "[*] Verifying environment files..." -ForegroundColor Blue
$backendEnv = Join-Path $BACKEND_DIR ".env"
$backendEnvExample = Join-Path $BACKEND_DIR ".env.example"
if (-not (Test-Path $backendEnv) -and (Test-Path $backendEnvExample)) {
    Write-Host "[!] backend\.env missing. Copying from .env.example..." -ForegroundColor Yellow
    Copy-Item $backendEnvExample $backendEnv
}

$rootEnvLocal = Join-Path $ROOT_DIR ".env.local"
$timelineEnvLocal = Join-Path $ROOT_DIR "timeline_studio\.env.local"
if ((Test-Path $rootEnvLocal) -and (-not (Test-Path $timelineEnvLocal))) {
    Write-Host "[*] Copying root .env.local to timeline_studio\.env.local..." -ForegroundColor Blue
    Copy-Item $rootEnvLocal $timelineEnvLocal
}

# ------------------------------------------------------------------------------
# 4. Frontend Dependencies Check
# ------------------------------------------------------------------------------
$nodeModulesDir = Join-Path $ROOT_DIR "timeline_studio\node_modules"
if (-not (Test-Path $nodeModulesDir)) {
    Write-Host "[!] timeline_studio\node_modules missing. Running npm install..." -ForegroundColor Yellow
    Push-Location (Join-Path $ROOT_DIR "timeline_studio")
    try {
        & npm install
    } finally {
        Pop-Location
    }
    Write-Host "[OK] Frontend dependencies installed." -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# 5. Launch Servers Concurrently
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "==============================================================" -ForegroundColor Green
Write-Host "  All systems ready! Launching Backend & Frontend..." -ForegroundColor Green
Write-Host "==============================================================" -ForegroundColor Green
Write-Host "  Frontend UI:  http://localhost:3000" -ForegroundColor Cyan
Write-Host "  Backend API:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "  API Docs:     http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "==============================================================" -ForegroundColor Green
Write-Host "  Press Ctrl+C to shut down both servers." -ForegroundColor Green
Write-Host "==============================================================" -ForegroundColor Green
Write-Host ""

$backendProcess = $null
$frontendProcess = $null

try {
    # Start Backend Process
    $backendPsi = New-Object System.Diagnostics.ProcessStartInfo
    $backendPsi.FileName = $VENV_PYTHON
    $backendPsi.Arguments = "-m uvicorn main:app --reload --port 8000"
    $backendPsi.WorkingDirectory = $BACKEND_DIR
    $backendPsi.UseShellExecute = $false
    $backendProcess = [System.Diagnostics.Process]::Start($backendPsi)

    # Start Frontend Process
    $frontendPsi = New-Object System.Diagnostics.ProcessStartInfo
    $frontendPsi.FileName = "cmd.exe"
    $frontendPsi.Arguments = "/c npm run dev"
    $frontendPsi.WorkingDirectory = (Join-Path $ROOT_DIR "timeline_studio")
    $frontendPsi.UseShellExecute = $false
    $frontendProcess = [System.Diagnostics.Process]::Start($frontendPsi)

    # Wait on both processes
    while (-not $backendProcess.HasExited -and -not $frontendProcess.HasExited) {
        Start-Sleep -Milliseconds 500
    }
}
finally {
    Write-Host ""
    Write-Host "[*] Stopping servers..." -ForegroundColor Yellow

    if ($backendProcess -and -not $backendProcess.HasExited) {
        try {
            $backendProcess.Kill()
        } catch {}
    }

    if ($frontendProcess -and -not $frontendProcess.HasExited) {
        try {
            $frontendProcess.Kill()
        } catch {}
    }

    Write-Host "[OK] Servers stopped cleanly." -ForegroundColor Green
}

