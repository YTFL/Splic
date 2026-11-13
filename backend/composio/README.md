# Splic Composio Integration Backend (Firebase Authentication)

Autonomous OAuth connection manager and controlled execution layer for **Instagram** and **YouTube** via **Composio**, secured with **Firebase Authentication (Admin SDK)**, built with **Python 3.11+**, **FastAPI**, and **Pydantic**.

This module is part of the **Splic** creator platform and runs as an independent, isolated service inside `backend/composio/`.

---

## 1. Architecture & Design Principles

```text
┌────────────────────────────────────────────────────────────────────────┐
│             FRONTEND CLIENT (Creator Dashboard / Timeline Studio)      │
│  • Signs in with Firebase Web SDK (using project credentials)          │
│  • Obtains Firebase ID Token: auth.currentUser.getIdToken()            │
│  • Attaches Header: Authorization: Bearer <FIREBASE_ID_TOKEN>          │
│  • Initiates Connect Request (POST /api/v1/composio/connect/instagram) │
│  • Redirects User to Composio Hosted OAuth Consent Page                │
│  • Polls/Checks Status (GET /api/v1/composio/connect/instagram/status) │
│  • Displays Safe Profile Summary (Handles, Followers, Channels)        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS + REST API (/api/v1)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   SPLIC COMPOSIO BACKEND (FastAPI)                     │
│  • Firebase Admin SDK Token Verifier (Signature, Expiration, Revocation)│
│  • Verified Firebase UID Extraction (Deterministic user tenant key)    │
│  • Multi-Tenant User Isolation (Creator A cannot view Creator B data)  │
│  • Connection Manager (OAuth links & account lifecycle via Composio)   │
│  • Token Sanitization Layer (Zero secrets/tokens exposed to frontend)   │
│  • Controlled Action Engine (Allowlisted read-only actions ONLY)       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Composio Python SDK (v3)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      COMPOSIO API INFRASTRUCTURE                       │
│  • Hosted OAuth Flows (Meta Graph API & Google OAuth 2.0)              │
│  • Toolkits & Actions Catalog (Instagram, YouTube)                     │
└────────────────────────────────────────────────────────────────────────┘
```

### Core Security Guarantees
1. **Verified Firebase User Identity:** Every authenticated request must carry a valid `Authorization: Bearer <FIREBASE_ID_TOKEN>`. The backend verifies the cryptographic signature with Google public keys and enforces revocation and expiration checks.
2. **Deterministic Multi-Tenant Isolation:** The verified Firebase UID is used as the tenant identifier for all Composio connections and account queries. Creator A (`uid_A`) can never query, inspect, or disconnect Creator B's accounts (`403 Forbidden`).
3. **Zero Frontend Secret Exposure:** Access tokens, refresh tokens, and OAuth secrets are never returned in any API response or written to logs.
4. **Controlled Action Allowlist:** Mutating actions (`INSTAGRAM_CREATE_POST`, `YOUTUBE_UPLOAD_VIDEO`) are strictly blocked with `403 Forbidden`. Only safe, non-destructive read-only queries are permitted.
5. **Isolated Module:** Code is strictly isolated inside `backend/composio/` and does not interfere with `backend/scrapper/` or the `timeline studio` frontend.

---

## 2. Directory Structure

```text
backend/composio/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app, CORS, lifespan, and error handlers
│   ├── config.py                   # Pydantic BaseSettings for env vars & validation
│   ├── dependencies.py             # Firebase Bearer token verification & service DI
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   └── firebase.py             # Firebase Admin SDK initialization & token verifier
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py           # GET /api/v1/health & GET /api/v1/ready
│   │       ├── composio.py         # /status, /toolkits, /actions, /execute
│   │       ├── instagram.py        # /connect/instagram, /accounts/instagram
│   │       ├── youtube.py          # /connect/youtube, /accounts/youtube
│   │       └── accounts.py         # /accounts, /accounts/{id}, DELETE /{id}
│   │
│   ├── integrations/
│   │   ├── __init__.py
│   │   └── composio/
│   │       ├── __init__.py
│   │       ├── client.py           # Composio client singleton & health checking
│   │       ├── sessions.py         # Composio user runtime session management
│   │       ├── connections.py      # OAuth link initiation & account sanitization
│   │       ├── toolkit_discovery.py# Instagram & YouTube discovery & allowlisting
│   │       └── execution.py        # Controlled action execution with security gates
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── account.py              # Pydantic models for connected accounts
│   │   ├── connection.py           # Pydantic models for OAuth requests/responses
│   │   └── action.py               # Pydantic models for toolkits & actions
│   │
│   └── services/
│       ├── __init__.py
│       ├── account_service.py      # High-level account queries & ownership logic
│       └── connection_service.py   # Connection orchestration for Instagram/YouTube
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Mock Composio client & Firebase token verifier
│   ├── test_health.py              # Health check & readiness unit tests
│   ├── test_composio.py            # Discovery, allowlist & execution tests
│   ├── test_connections.py         # OAuth initiation & ownership validation tests
│   └── test_firebase_auth.py       # Dedicated Firebase token & tenant isolation tests
│
├── .env.example                    # Safe template for environment variables
├── .gitignore                      # Git exclusion rules
├── requirements.txt                # Pinned production and test dependencies
└── README.md                       # Complete documentation and run instructions
```

---

## 3. Prerequisites

- **Python 3.11+**
- **pip** and `venv`
- **Firebase Project:** Configured in root `/.env.local` (`FIREBASE_PROJECT_ID`) with Authentication enabled.
- **Composio Account:** API key from [app.composio.dev/settings](https://app.composio.dev/settings).

---

## 4. Installation & Setup

### macOS / Linux

```bash
cd backend/composio

# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
cd backend\composio

# 1. Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt
```

---

## 5. Environment Configuration

All environment variables for the Composio backend (including Firebase Admin and Composio credentials) are loaded from the **single project root file**:

`/.env.local`

The backend resolves the path to `/.env.local` deterministically relative to `backend/composio/app/config.py`, ensuring consistent variable loading whether the server is started from the repository root, from `backend/composio/`, or from any other working directory.

Configure your root `/.env.local`:

```env
# ==============================================================================
# Splic Project Root Environment Configuration (/.env.local)
# ==============================================================================

# Section 1: Frontend Firebase Web SDK (Public - NEXT_PUBLIC_*)
NEXT_PUBLIC_FIREBASE_API_KEY=AIzaSy...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=splic-app.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=splic-app
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=splic-app.firebasestorage.app
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=123456789012
NEXT_PUBLIC_FIREBASE_APP_ID=1:123456789012:web:abcdef...

# Section 2: Backend Firebase Admin (Private)
FIREBASE_PROJECT_ID=splic-app
# Single-line service account JSON string (keep private and do not commit)
FIREBASE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"splic-app",...}

# Section 3: Composio API Credentials (Private)
COMPOSIO_API_KEY=your_composio_api_key_here

# Section 4: Server & CORS Networking
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development
LOG_LEVEL=INFO

FRONTEND_URL=http://localhost:3000,http://localhost:5173
BACKEND_URL=http://localhost:8000
OAUTH_REDIRECT_URL=http://localhost:3000/auth/callback
```

---

## 6. Running the Backend

### Start the Server (macOS / Linux)

```bash
cd backend/composio
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Start the Server (Windows PowerShell)

```powershell
cd backend\composio
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

* **Interactive Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Interactive ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **API Health:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## 7. Frontend Integration Contract

### 7.1 Client Authentication Flow
1. The Creator Dashboard frontend initializes Firebase using its Web SDK configuration:
   ```typescript
   import { initializeApp } from "firebase/app";
   import { getAuth } from "firebase/auth";

   const app = initializeApp({
     projectId: "splic-app",
     apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
     authDomain: "splic-app.firebaseapp.com",
   });
   export const auth = getAuth(app);
   ```
2. When calling any backend endpoint under `/api/v1/composio/*`:
   ```typescript
   const idToken = await auth.currentUser?.getIdToken();

   const response = await fetch("http://localhost:8000/api/v1/composio/accounts", {
     headers: {
       "Authorization": `Bearer ${idToken}`,
       "Content-Type": "application/json",
     },
   });
   ```

### 7.2 Backend Verification
- If `Authorization` header is missing or malformed -> **401 Unauthorized**.
- If token has expired -> **401 Unauthorized** (`"Firebase ID token has expired."`).
- If token has been revoked -> **401 Unauthorized** (`"Firebase ID token has been revoked."`).
- If token signature is invalid -> **401 Unauthorized** (`"Invalid Firebase ID token."`).

---

## 8. API Reference (`/api/v1`)

All authenticated endpoints require `Authorization: Bearer <FIREBASE_ID_TOKEN>`.

### 8.1 Health & Diagnostics

| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Public | Returns service status and Composio SDK integration readiness. |
| `GET` | `/api/v1/ready` | Public | Container readiness probe. |
| `GET` | `/api/v1/composio/status` | Bearer Token | Returns SDK status and verified user UID context. |

### 8.2 OAuth Connections (Instagram & YouTube)

| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/composio/connect/instagram` | Bearer Token | Generates a Composio hosted OAuth authorization URL for Instagram. |
| `GET` | `/api/v1/composio/connect/instagram/status` | Bearer Token | Checks if authenticated Firebase user has an active Instagram connection. |
| `POST` | `/api/v1/composio/connect/youtube` | Bearer Token | Generates a Composio hosted OAuth authorization URL for YouTube. |
| `GET` | `/api/v1/composio/connect/youtube/status` | Bearer Token | Checks if authenticated Firebase user has an active YouTube connection. |

### 8.3 Connected Account Management

| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/composio/accounts` | Bearer Token | Lists all accounts connected by the authenticated user. |
| `GET` | `/api/v1/composio/accounts/instagram` | Bearer Token | Lists connected Instagram accounts for user. |
| `GET` | `/api/v1/composio/accounts/youtube` | Bearer Token | Lists connected YouTube accounts for user. |
| `GET` | `/api/v1/composio/accounts/{account_id}` | Bearer Token | Detailed sanitized metadata for an account (enforces UID ownership). |
| `DELETE` | `/api/v1/composio/accounts/{account_id}` | Bearer Token | Disconnects and revokes an account (enforces UID ownership). |

### 8.4 Toolkit & Action Discovery

| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/composio/toolkits` | Bearer Token | Lists available toolkits (`instagram`, `youtube`). |
| `GET` | `/api/v1/composio/actions/{toolkit}` | Bearer Token | Lists actions under a toolkit and indicates allowlist status. |
| `POST` | `/api/v1/composio/execute` | Bearer Token | Executes an allowlisted read-only tool. Blocked mutating tools return `403`. |

---

## 9. Running Automated Tests

The test suite runs both with `pytest` and with Python's built-in `unittest` runner. All external Firebase and Composio calls are mocked offline for automated testing.

### Run with Python unittest (Zero External Test Runner Required)

```bash
# macOS / Linux
cd backend/composio
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11 -m unittest discover tests

# Windows PowerShell
cd backend\composio
python -m unittest discover tests
```

### Run with pytest

```bash
# macOS / Linux
pytest tests/ -v

# Windows PowerShell
pytest tests\ -v
```

---

## 10. Strict Out-of-Scope Notice

In accordance with architectural boundaries:
- The scraper module belongs to `backend/scrapper/` and is completely separate.
- The Timeline Studio editor (`timeline studio/`) is completely untouched.
- The Creator Dashboard frontend is untouched and communicates strictly via REST API + Firebase ID tokens.
- Automatic posting or publishing is strictly blocked with `403 Forbidden`.
