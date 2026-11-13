# Splic Firebase Architecture & Configuration Guide

This directory contains the documentation and architectural guide for the **Splic** Firebase integration.

Both the **Creator Dashboard frontend** and the **FastAPI backend** share the same Firebase project identity (`projectId: "splic-app"`), enabling seamless client-to-server token authentication.

---

## 1. Directory Contents

```text
firebase/
└── README.md               # This architectural and integration guide
```

> [!NOTE]
> `firebase.config.json` was deprecated and removed. All Firebase project configuration is managed centrally via the root `.env.local` file (using `FIREBASE_PROJECT_ID`, etc.), preventing duplicated configuration files across the repository.

---

## 2. Frontend Web Configuration vs. Private Admin Credentials

Understanding the boundary between client configuration and server-side private credentials is essential for platform security.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   FIREBASE WEB APP CONFIGURATION                       │
│  Source: Root .env.local (NEXT_PUBLIC_FIREBASE_* / VITE_FIREBASE_*)    │
│  Contents: apiKey, authDomain, projectId, appId                        │
│  Sensitivity: Non-secret project metadata                              │
│  Usage: Bundled into Frontend (Creator Dashboard) via Web SDK          │
└────────────────────────────────────────────────────────────────────────┘

                                   VS.

┌────────────────────────────────────────────────────────────────────────┐
│                  FIREBASE ADMIN SERVICE ACCOUNT KEY                    │
│  Source: Root .env.local (FIREBASE_SERVICE_ACCOUNT_JSON)               │
│  Contents: private_key_id, private_key (RSA 2048-bit), client_email    │
│  Sensitivity: STRICTLY CONFIDENTIAL PRIVILEGED CREDENTIAL             │
│  Usage: Backend ONLY (FastAPI Composio Service). NEVER in git/client.  │
└────────────────────────────────────────────────────────────────────────┘
```

> [!CAUTION]
> **Never commit service account JSON or private keys to Git.**  
> Service account credentials grant administrative privileges to your Firebase and Google Cloud project. They must only be stored securely in the local root `.env.local` as a single-line string (`FIREBASE_SERVICE_ACCOUNT_JSON`).

---

## 3. How to Obtain & Populate Firebase Configuration

### 3.1 Step 1: Create a Project in Firebase Console
1. Go to the [Firebase Console](https://console.firebase.google.com/).
2. Click **Add project** and name it `splic-app` (or your chosen project ID).
3. Disable Google Analytics (or keep default) and finish creation.

### 3.2 Step 2: Enable Firebase Authentication
1. In the Firebase console left menu, navigate to **Build > Authentication**.
2. Click **Get Started**.
3. Under the **Sign-in method** tab, enable the desired identity providers:
   - **Email/Password**
   - **Google** (recommended for Indian creators)

### 3.3 Step 3: Register a Web App & Copy Configuration
1. Go to **Project Settings** (gear icon) > **General**.
2. Under **Your apps**, click the Web icon (`</>`) to add a web app (name: `Splic Dashboard`).
3. Store the configuration values in the root `.env.local`:
   ```env
   FIREBASE_PROJECT_ID=your-project-id
   # Web SDK client variables (if frontend uses Vite or Next.js):
   # VITE_FIREBASE_API_KEY=AIzaSy...
   # VITE_FIREBASE_AUTH_DOMAIN=your-project-id.firebaseapp.com
   # VITE_FIREBASE_PROJECT_ID=your-project-id
   ```

### 3.4 Step 4: Configure Backend Service Account Key
1. In **Project Settings**, switch to the **Service accounts** tab.
2. Under **Firebase Admin SDK**, select **Python**.
3. Click **Generate new private key** and download the JSON file.
4. Convert the JSON file contents to a single-line string (e.g. `tr -d '\n' < your-key.json`).
5. Store the values directly in the root `.env.local`:
   ```env
   FIREBASE_PROJECT_ID=your-project-id
   FIREBASE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"your-project-id",...}
   ```

---

## 4. Frontend Integration Contract (Creator Dashboard)

The frontend initializes the official Firebase Web SDK using environment variables or configuration loaded from the root `.env.local`:

```typescript
import { initializeApp } from "firebase/app";
import { getAuth, signInWithPopup, GoogleAuthProvider } from "firebase/auth";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || import.meta.env.VITE_FIREBASE_PROJECT_ID || "splic-app",
};

// 1. Initialize Firebase Web client
const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

// 2. Authenticate User & Acquire ID Token
export async function getAuthenticatedBackendHeaders(): Promise<Record<string, string>> {
  const currentUser = auth.currentUser;
  if (!currentUser) {
    throw new Error("No user is currently signed in to Firebase.");
  }
  
  // Obtain fresh ID token
  const idToken = await currentUser.getIdToken();
  
  return {
    "Authorization": `Bearer ${idToken}`,
    "Content-Type": "application/json",
  };
}
```

---

## 5. Backend Verification Contract (FastAPI)

1. The frontend attaches the token in the request:
   ```http
   GET /api/v1/composio/accounts HTTP/1.1
   Host: localhost:8000
   Authorization: Bearer <FIREBASE_ID_TOKEN>
   ```
2. The FastAPI `get_current_user` dependency intercepts the Bearer token.
3. The Firebase Admin SDK verifies token validity, signature, expiration, and revocation status:
   ```python
   decoded_token = auth.verify_id_token(token, check_revoked=True)
   uid = decoded_token["uid"]
   ```
4. The verified `uid` becomes the tenant boundary for Composio operations, ensuring complete isolation across creators.

