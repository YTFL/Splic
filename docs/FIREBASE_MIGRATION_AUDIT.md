# Splic Firebase Authentication Migration Audit

**Date:** 2026-11-13  
**Auditor:** Senior Software Architect & Python/Firebase Authentication Engineer  
**Status:** Audit Complete — Ready for Migration  

---

## 1. Executive Summary

This audit assesses the current state of the Splic workspace, inspects all existing authentication mechanisms and Supabase dependencies, documents the boundaries of teammate-owned components, and designs the migration of the `backend/composio` service to **Firebase Authentication** using the **Firebase Admin SDK** alongside root-level shared Web SDK configuration.

---

## 2. Existing Workspace & Architecture Analysis

### 2.1 Directory Structure & Ownership Map

| Directory / File | Ownership | Status & Boundary Guard |
| :--- | :--- | :--- |
| `timeline studio/` | Teammate A | Cloned and modified React/Vite video editor (WebCodecs MP4 export). **READ-ONLY — Untouched.** |
| Creator Dashboard | Teammate B | External/parallel frontend. To be integrated separately using `firebase/firebase.config.json` and Bearer token auth. **Untouched.** |
| `backend/scrapper/` | Teammate C | Scraper module space. **Untouched.** |
| `backend/composio/` | Target Module | FastAPI service handling Instagram & YouTube OAuth connections via Composio. Migrating auth to Firebase. |
| `firebase/` | Shared (New) | Root-level shared non-secret Firebase configuration (`firebase.config.json`) and developer guide (`README.md`). |

### 2.2 Existing Backend & Authentication Assessment
1. **Current Backend Architecture:**
   - Framework: FastAPI + Pydantic v2 + Uvicorn.
   - Modules: Cleanly layered (`api/routes/`, `integrations/composio/`, `schemas/`, `services/`).
   - Test Suite: 23 passing tests covering health, connection initiation, account listing, ownership validation, and action allowlisting.
2. **Current Authentication Mechanism:**
   - In `backend/composio/app/dependencies.py`, the user identity was previously resolved via an `X-User-ID` header, optional query parameter, a placeholder PyJWT hook for `SUPABASE_JWT_SECRET`, or a development fallback to `COMPOSIO_USER_ID`.
   - **Vulnerability / Limitation:** Arbitrary `X-User-ID` headers could be supplied in requests, and all users defaulted to a single shared `COMPOSIO_USER_ID` in development.
3. **Supabase References to Remove:**
   - `SUPABASE_URL` in `config.py` and `.env.example`.
   - `SUPABASE_JWT_SECRET` in `config.py`, `dependencies.py`, and `.env.example`.
   - Obsolete `PyJWT` dependency references.
   - Documentation notes referencing Supabase in `backend/composio/README.md`.

---

## 3. Required Firebase Architecture & Shared Configuration

```text
Splic/
├── firebase/
│   ├── firebase.config.json      # Non-secret Firebase Web client configuration
│   └── README.md                 # Setup guide, Web vs Admin SDK differentiation
│
├── frontend/ (or dashboard)      # Consumes firebase.config.json via Firebase Web SDK
│
├── backend/
│   ├── composio/                 # Verifies ID tokens using Firebase Admin Python SDK
│   │   ├── app/
│   │   │   ├── auth/
│   │   │   │   └── firebase.py   # Firebase Admin initialization & token verification
│   │   │   └── dependencies.py   # Bearer token extraction & user identity mapping
│   │   └── tests/                # Test suite with mock Firebase token verification
│   └── scrapper/                 # Teammate's scraper (untouched)
│
├── timeline studio/              # Video editor (untouched)
└── .gitignore                    # Updated to strictly exclude service account private keys
```

### 3.1 Credential & Security Separation

| Item | Intended Target | Exposure Level | Storage Location |
| :--- | :--- | :--- | :--- |
| **Firebase Web Config** (`apiKey`, `authDomain`, `projectId`, `appId`, etc.) | Frontend & Shared Docs | Public project metadata (non-secret) | `firebase/firebase.config.json` |
| **Firebase Admin Service Account** (private keys, client email) | Backend Only | **Strictly Private / Confidential** | `GOOGLE_APPLICATION_CREDENTIALS` (JSON path outside git) |
| **Firebase ID Token** (JWT signed by Google) | Network (HTTPS) | Ephemeral Bearer credential (1-hour lifespan) | Transmitted via `Authorization: Bearer <TOKEN>` |

---

## 4. Firebase UID to Composio Identity Mapping Strategy

1. **Deterministic User Isolation:**
   Every user authenticated via Firebase has a globally unique, permanent `uid` (e.g. `firebase_usr_7x9Q...`).
2. **Composio User Identity:**
   Instead of using a global shared `COMPOSIO_USER_ID`, each Firebase `uid` is passed directly as the `user_id` to Composio:
   ```python
   composio_user_id = f"splic_{firebase_uid}"  # or direct firebase_uid
   ```
3. **Multi-Tenant Protection:**
   - When a creator calls `/api/v1/composio/connect/instagram` or `/youtube`, their verified Firebase UID is passed into Composio's session / connection manager.
   - Account listing and account deletion verify that `account.user_id == authenticated_user.id`.
   - Creator A (`uid_A`) can never query, view, or disconnect social accounts owned by Creator B (`uid_B`).

---

## 5. Files to Be Created & Modified

### New Files
- `firebase/firebase.config.json`: Standardized public web configuration.
- `firebase/README.md`: Architecture guide, setup instructions, credential rules.
- `backend/composio/app/auth/__init__.py`: Auth subpackage.
- `backend/composio/app/auth/firebase.py`: Firebase Admin SDK lifecycle, token verifier, and mock support for unit tests.
- `backend/composio/tests/test_firebase_auth.py`: Unit tests for token verification, invalid tokens, expired tokens, revoked tokens, and UID extraction.
- `docs/FIREBASE_MIGRATION_AUDIT.md`: This audit document.

### Modified Files (Surgical & Isolated)
- `backend/composio/app/config.py`: Remove `SUPABASE_*`, add `FIREBASE_PROJECT_ID` and `GOOGLE_APPLICATION_CREDENTIALS`.
- `backend/composio/app/dependencies.py`: Replace arbitrary header logic and Supabase JWT decoding with strict Firebase token verification.
- `backend/composio/app/integrations/composio/client.py`: Remove global fallback assumption.
- `backend/composio/.env.example`: Update environment variables to reflect Firebase.
- `backend/composio/requirements.txt`: Ensure `firebase-admin>=6.5.0` is pinned.
- `backend/composio/tests/conftest.py`: Add mock Firebase token fixtures to preserve 100% of existing 23 tests without external network dependencies.
- `backend/composio/README.md`: Update documentation to reflect Firebase authentication and updated API contract.
- Root `.gitignore`: Add rules to prevent accidental commits of `*serviceAccount*.json` and `*.service-account.json`.

---

## 6. Migration Verification Checklist

1. [x] Zero changes to `timeline studio/`.
2. [x] Zero changes to `backend/scrapper/`.
3. [x] Single-source configuration consolidated in root `.env.local` (redundant `firebase/firebase.config.json` deleted).
4. [x] Private credentials strictly guarded by `.gitignore` and backend environment variables.
5. [x] All 23 original regression tests continue to pass.
6. [x] New dedicated Firebase authentication tests pass.
7. [x] Frontend authentication contract documented clearly for the Creator Dashboard team.

---

## 7. Addendum: Removal of Redundant `firebase.config.json`

To eliminate configuration fragmentation across the repository:
- `firebase/firebase.config.json` was deleted.
- `backend/composio/app/config.py` was updated to remove `_discover_root_firebase_project_id()` and file reads of `firebase.config.json`.
- All Firebase Admin backend settings (`FIREBASE_PROJECT_ID`, `GOOGLE_APPLICATION_CREDENTIALS`) and client project configurations are sourced exclusively from the root `.env.local`.

