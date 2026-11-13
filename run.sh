#!/usr/bin/env bash
# ==============================================================================
# SPLIC — Single-File Runner (macOS, Linux, & Git Bash)
# Launches both the FastAPI backend and Next.js frontend concurrently.
# ==============================================================================

set -eo pipefail

# ANSI color codes
BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Determine repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BOLD}${CYAN}"
echo "=============================================================="
echo "          SPLIC — Indic Video Auto-Editor Runner              "
echo "=============================================================="
echo -e "${NC}"

# ------------------------------------------------------------------------------
# 1. Dependency Checks: Node.js & npm
# ------------------------------------------------------------------------------
echo -e "${BLUE}[*] Checking Node.js and npm...${NC}"
if ! command -v node >/dev/null 2>&1; then
  echo -e "${RED}[ERROR] Node.js is not installed or not in PATH.${NC}"
  echo "Please install Node.js (v18+ or v20+ recommended) from https://nodejs.org/"
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo -e "${RED}[ERROR] npm is not installed or not in PATH.${NC}"
  exit 1
fi
echo -e "${GREEN}[✓] Node $(node -v) & npm $(npm -v) found.${NC}"

# ------------------------------------------------------------------------------
# 2. Dependency Checks: Python
# ------------------------------------------------------------------------------
echo -e "${BLUE}[*] Checking Python environment...${NC}"

# Detect OS for venv binary folder (bin vs Scripts on Windows/Git Bash)
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
  VENV_BIN_SUBDIR="Scripts"
  PYTHON_EXE_NAME="python.exe"
else
  VENV_BIN_SUBDIR="bin"
  PYTHON_EXE_NAME="python"
fi

BACKEND_DIR="$SCRIPT_DIR/backend"
VENV_DIR="$BACKEND_DIR/.venv"
VENV_PYTHON="$VENV_DIR/$VENV_BIN_SUBDIR/$PYTHON_EXE_NAME"

# Locate a system python (prefer 3.11, 3.12, 3.10, then python3, python)
find_system_python() {
  for py in python3.11 python3.12 python3.10 python3 python; do
    if command -v "$py" >/dev/null 2>&1; then
      echo "$py"
      return 0
    fi
  done
  return 1
}

# Ensure venv exists
if [ ! -f "$VENV_PYTHON" ]; then
  SYSTEM_PY=$(find_system_python || true)
  if [ -z "$SYSTEM_PY" ]; then
    echo -e "${RED}[ERROR] Python 3 was not found in PATH.${NC}"
    echo "Please install Python 3.10+ from https://www.python.org/"
    exit 1
  fi

  echo -e "${YELLOW}[!] Python virtual environment not found in backend/.venv.${NC}"
  echo -e "${BLUE}[*] Creating virtual environment using $SYSTEM_PY...${NC}"
  "$SYSTEM_PY" -m venv "$VENV_DIR"

  echo -e "${BLUE}[*] Installing backend dependencies from requirements.txt...${NC}"
  "$VENV_PYTHON" -m pip install --upgrade pip
  "$VENV_PYTHON" -m pip install -r "$BACKEND_DIR/requirements.txt"
  echo -e "${GREEN}[✓] Backend virtual environment created and configured.${NC}"
else
  echo -e "${GREEN}[✓] Existing virtual environment found: $VENV_DIR${NC}"
fi

# ------------------------------------------------------------------------------
# 3. Environment Files Setup
# ------------------------------------------------------------------------------
echo -e "${BLUE}[*] Verifying environment files...${NC}"

# Backend .env
if [ ! -f "$BACKEND_DIR/.env" ]; then
  if [ -f "$BACKEND_DIR/.env.example" ]; then
    echo -e "${YELLOW}[!] backend/.env missing. Creating from .env.example (mock mode enabled)...${NC}"
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
  fi
fi

# Frontend .env.local (link or copy from root if present)
TIMELINE_DIR="$SCRIPT_DIR/timeline_studio"
if [ -f "$SCRIPT_DIR/.env.local" ] && [ ! -f "$TIMELINE_DIR/.env.local" ]; then
  echo -e "${BLUE}[*] Linking root .env.local into timeline_studio/...${NC}"
  # Use symlink where supported, fallback to copy
  ln -sf "../.env.local" "$TIMELINE_DIR/.env.local" 2>/dev/null || cp "$SCRIPT_DIR/.env.local" "$TIMELINE_DIR/.env.local"
fi

# ------------------------------------------------------------------------------
# 4. Frontend Dependencies Check
# ------------------------------------------------------------------------------
if [ ! -d "$TIMELINE_DIR/node_modules" ]; then
  echo -e "${YELLOW}[!] timeline_studio/node_modules missing. Running npm install...${NC}"
  (cd "$TIMELINE_DIR" && npm install)
  echo -e "${GREEN}[✓] Frontend dependencies installed.${NC}"
fi

# ------------------------------------------------------------------------------
# 5. Port Conflict Check (8000 and 3000)
# ------------------------------------------------------------------------------
check_port() {
  local port=$1
  local name=$2
  if command -v lsof >/dev/null 2>&1; then
    local pid
    pid=$(lsof -ti :"$port" 2>/dev/null || true)
    if [ -n "$pid" ]; then
      echo -e "${YELLOW}[WARNING] Port $port ($name) is currently occupied by PID $pid.${NC}"
      echo -e "${YELLOW}          If you run into bind errors, terminate PID $pid with: kill $pid${NC}"
    fi
  fi
}

check_port 8000 "FastAPI Backend"
check_port 3000 "Next.js Frontend"

# ------------------------------------------------------------------------------
# 6. Process Cleanup Handler
# ------------------------------------------------------------------------------
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  trap - SIGINT SIGTERM EXIT
  echo ""
  echo -e "${YELLOW}[*] Stopping Splic servers...${NC}"

  if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi

  if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi

  # Allow 1 second for graceful shutdown
  sleep 1

  # Force kill if still running
  if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill -9 "$FRONTEND_PID" 2>/dev/null || true
  fi

  if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill -9 "$BACKEND_PID" 2>/dev/null || true
  fi

  echo -e "${GREEN}[✓] Both servers shut down cleanly.${NC}"
  exit 0
}

trap cleanup INT TERM EXIT

# ------------------------------------------------------------------------------
# 7. Launch Servers Concurrently
# ------------------------------------------------------------------------------
echo ""
echo -e "${BOLD}${GREEN}=============================================================="
echo "  All systems ready! Launching Backend & Frontend..."
echo "=============================================================="
echo -e "  Frontend UI:  ${CYAN}http://localhost:3000${GREEN}"
echo -e "  Backend API:  ${CYAN}http://localhost:8000${GREEN}"
echo -e "  API Docs:     ${CYAN}http://localhost:8000/docs${GREEN}"
echo "=============================================================="
echo -e "  Press ${BOLD}Ctrl+C${NC}${GREEN} at any time to shut down both servers."
echo -e "==============================================================${NC}"
echo ""

# Start FastAPI backend
(
  cd "$BACKEND_DIR"
  exec "$VENV_PYTHON" -m uvicorn main:app --reload --port 8000
) &
BACKEND_PID=$!

# Start Next.js frontend
(
  cd "$TIMELINE_DIR"
  exec npm run dev
) &
FRONTEND_PID=$!

# Wait for either background process to exit or signal received
while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
  sleep 1
done
