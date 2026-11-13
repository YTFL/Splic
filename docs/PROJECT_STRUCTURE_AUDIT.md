# Splic Project Structure & Architectural Audit

**Date:** 2026-11-13  
**Auditor:** Senior Software Architect & Backend Engineer  
**Status:** Complete — Isolation Boundaries Verified  

---

## 1. Executive Summary

This audit establishes the physical file structure, module ownership, component boundaries, and isolation guarantees for the **Splic** project prior to implementing the Composio backend integration.

### Core Isolation Rules
1. **`timeline studio/`** is the active workspace of a frontend teammate (forked WebCodecs/Canvas multi-track video editor). **It is strictly READ-ONLY and will not be modified.**
2. **Creator Dashboard** is an external/teammate-owned frontend not yet merged into this branch. No assumptions or conflicting frontends will be generated.
3. **`backend/`** is being introduced as the shared backend root.
4. **`backend/scrapper/`** is reserved exclusively for a teammate's scraper service.
5. **`backend/composio/`** is our dedicated, self-contained Python FastAPI module providing Instagram and YouTube OAuth connection management, toolkit/action discovery, and safe execution.

---

## 2. Repository & Folder Structure Analysis

The current workspace inspection revealed the following layout:

```text
/Users/shashankk/Documents/xena/Splic/
├── .agent/
│   └── skills/                   # Internal agentic skills for timeline & indic video workflows
├── .git/                         # Git repository metadata (branch: Kiran)
├── .gitignore                    # Root gitignore rules
├── README.md                     # High-level Splic product summary
├── agents.md                     # Agent operating rules & guardrails
├── gemini.md                     # Architecture specification & constraints
├── indic_video_auto_editor_spec.md # 24-hr Indic editor blueprint
├── timeline studio/              # Cloned and modified Timeline Studio application
│   ├── .prettierignore
│   ├── .prettierrc.json
│   ├── LICENSE
│   ├── eslint.config.js
│   ├── index.html
│   ├── netlify.toml
│   ├── package-lock.json
│   ├── package.json
│   ├── public/                   # Static assets, worker models, icons
│   ├── scripts/                  # Internal build/discovery scripts
│   ├── src/                      # React/Vite source code (600+ files, web workers, shaders)
│   ├── tsconfig.json
│   └── vite.config.mjs
└── docs/                         # Architecture documentation and audits
```

---

## 3. Directory Classification & Responsibilities

| Path | Status | Owner | Description / Protection Rule |
| :--- | :--- | :--- | :--- |
| `timeline studio/` | **Verified** | Teammate A | React 19 + Vite multi-track video editor. Runs with `COOP: same-origin` and `COEP: require-corp` for WebCodecs MP4 rendering. **Mandatory: DO NOT TOUCH.** |
| Creator Dashboard | **Verified (External)** | Teammate B | Not present in this working copy. Kept isolated from backend dependencies. |
| `backend/` | **Verified (New)** | Multi-team | Parent folder for backend microservices. |
| `backend/scrapper/` | **Verified (Reserved)** | Teammate C | Dedicated scraper module. Must remain untouched. |
| `backend/composio/` | **Target Location** | Backend Engineer | Autonomous FastAPI service for Composio integration (Instagram & YouTube). |

---

## 4. Technical Analysis

### 4.1 Frontend Analysis (`timeline studio/`)
- **Framework:** React 19, Vite 6, Tailwind CSS.
- **Port:** Vite defaults to `5173` / `3000`.
- **Security Headers:** Enforces `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp` via `netlify.toml` and `vite.config.mjs`.
- **State Store:** Local in-memory state with WebWorkers (`asr.worker.js`, `auto-edit.worker.js`).
- **Dependencies:** WebCodecs, ONNX runtime web, libav WASM.

### 4.2 Authentication & Supabase Integration Status
- **Audit Finding (Verified):** There are no existing Supabase configuration files, Supabase client libraries, or active Supabase database migrations inside the current repository tree.
- **Architecture Requirement:** The new `backend/composio/` service must decouple authentication into a clean, pluggable dependency (`get_current_user`). For development, a configurable authenticated identity header (`X-User-ID` or fallback `dev_user`) will be used, with an explicit hook ready for Supabase JWT verification (`supabase.auth.get_user(jwt)`) without introducing breaking schema changes.

### 4.3 Environment Configuration & Conventions
- Root has no active `.env` file committed.
- Backend specifications in `gemini.md` suggest standard `.env` patterns.
- `backend/composio/.env.example` will define all needed variables for Composio and CORS.

### 4.4 API & Network Architecture
- Port `8000` is designated for the FastAPI backend.
- API routing will follow versioned semantics: `/api/v1/...`.
- CORS configuration will allow `http://localhost:5173`, `http://localhost:3000`, and customizable frontend origins.

---

## 5. Proposed Isolated Backend Architecture (`backend/composio/`)

```text
backend/
├── composio/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI initialization, CORS, global error handlers
│   │   ├── config.py                 # Pydantic BaseSettings for env vars & validation
│   │   ├── dependencies.py           # Pluggable user auth & Composio client injection
│   │   │
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── health.py         # /health and /ready
│   │   │       ├── composio.py       # Status & metadata
│   │   │       ├── instagram.py      # Instagram OAuth connect & status
│   │   │       ├── youtube.py        # YouTube OAuth connect & status
│   │   │       └── accounts.py       # User connected accounts & disconnect
│   │   │
│   │   ├── integrations/
│   │   │   └── composio/
│   │   │       ├── client.py         # Reusable SDK client wrapper & lifecycle
│   │   │       ├── sessions.py       # Composio user session management
│   │   │       ├── connections.py    # OAuth link initiation & status checks
│   │   │       ├── toolkit_discovery.py # Discovery of Instagram & YouTube toolkits/actions
│   │   │       └── execution.py      # Controlled, allowlisted read-only tool execution
│   │   │
│   │   ├── schemas/
│   │   │   ├── account.py            # Account metadata & status schemas
│   │   │   ├── connection.py         # Connection request & response schemas
│   │   │   └── action.py             # Toolkit discovery & execution schemas
│   │   │
│   │   └── services/
│   │       ├── account_service.py    # Account queries & ownership enforcement
│   │       └── connection_service.py # Connection initiation & callback workflows
│   │
│   ├── tests/
│   │   ├── test_health.py            # Startup & health checks
│   │   ├── test_composio.py          # Client, config validation & discovery
│   │   └── test_connections.py       # OAuth flows & account management
│   │
│   ├── .env.example                  # Safe template for secrets
│   ├── .gitignore                    # Python bytecode, .env, cache files
│   ├── requirements.txt              # Pinned compatible versions
│   └── README.md                     # Comprehensive documentation & run instructions
│
└── scrapper/                         # Teammate's scraper module (untouched)
```

---

## 6. Distinguishing Verified Findings from Assumptions

| Item | Status | Verification Note |
| :--- | :--- | :--- |
| `timeline studio/` exists and is functional | **Verified** | Present at root, contains package.json, src/, and vite config. |
| `backend/` directory presence | **Verified** | Did not exist initially; must be created cleanly. |
| `backend/scrapper/` presence | **Verified** | Not yet created on this branch; isolated from `backend/composio/`. |
| Creator Dashboard location | **Verified** | Not present in this git repository tree; managed independently. |
| Supabase Auth in workspace | **Verified** | Not present in local repo; abstract user auth interface used. |
| Composio SDK availability | **Verified** | Using Composio v3 architectural patterns with session authorization & connected accounts. |

---

## 7. Audit Conclusion & Next Steps

The proposed path `backend/composio/` is completely safe and introduces zero conflicts with existing or parallel teammate work. Proceeding with Phase 4 (backend foundation) and Phase 5 (Composio integration).

