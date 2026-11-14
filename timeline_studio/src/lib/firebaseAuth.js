/**
 * Firebase Web SDK authentication service for Splic Studio.
 *
 * The public Firebase configuration is read from the repository root `.env.local`
 * file (see `.env.example`) through the NEXT_PUBLIC_* variables that Next.js
 * inlines into the browser bundle. The Firebase SDK modules are imported lazily
 * so the studio still boots when the project is not configured yet.
 */

const STORAGE_KEY = "splic_auth_user";

export class AuthError extends Error {
  constructor(message, code = "auth/unknown") {
    super(message);
    this.name = "AuthError";
    this.code = code;
  }
}

function readFirebaseConfig() {
  return {
    apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || "",
    authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || "",
    projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "",
    storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || "",
    messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || "",
    appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || "",
  };
}

export function isFirebaseConfigured() {
  const config = readFirebaseConfig();
  return Boolean(config.apiKey && config.projectId);
}

let authRuntimePromise = null;

async function getAuthRuntime() {
  if (!isFirebaseConfigured()) {
    throw new AuthError(
      "Firebase is not configured. Add the NEXT_PUBLIC_FIREBASE_* variables to the repository root .env.local file.",
      "auth/not-configured",
    );
  }

  if (!authRuntimePromise) {
    authRuntimePromise = (async () => {
      const [appModule, authModule] = await Promise.all([
        import("firebase/app"),
        import("firebase/auth"),
      ]);
      const app = appModule.getApps().length
        ? appModule.getApp()
        : appModule.initializeApp(readFirebaseConfig());
      const auth = authModule.getAuth(app);
      return { app, auth, authModule };
    })().catch((error) => {
      authRuntimePromise = null;
      throw error;
    });
  }

  return authRuntimePromise;
}

function buildProfile(user, extra = {}) {
  const email = user?.email || "";
  const fallbackName = email ? email.split("@")[0] : "Indic Creator";
  return {
    uid: user?.uid || "",
    name: user?.displayName || fallbackName,
    email,
    photoURL: user?.photoURL || "",
    provider: user?.providerData?.[0]?.providerId || "password",
    isGuest: false,
    ...extra,
  };
}

function persistSession(profile) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
  } catch (_error) {
    // Ignore storage quota / private-mode failures: the session still lives in memory.
  }
}

function clearSession() {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch (_error) {
    // Nothing to clean up.
  }
}

export function getStoredSession() {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (_error) {
    return null;
  }
}

export function isSignedIn() {
  return Boolean(getStoredSession());
}

export async function signInWithEmail(email, password) {
  const { auth, authModule } = await getAuthRuntime();
  const credential = await authModule.signInWithEmailAndPassword(auth, email, password);
  const profile = buildProfile(credential.user);
  persistSession(profile);
  return profile;
}

export async function signUpWithEmail(email, password, displayName) {
  const { auth, authModule } = await getAuthRuntime();
  const credential = await authModule.createUserWithEmailAndPassword(auth, email, password);
  if (displayName) {
    try {
      await authModule.updateProfile(credential.user, { displayName });
    } catch (_error) {
      // A missing display name must not block account creation.
    }
  }
  const profile = buildProfile(credential.user, { provider: "password" });
  persistSession(profile);
  return profile;
}

export async function signInWithGoogle({ scopes = [] } = {}) {
  const { auth, authModule } = await getAuthRuntime();
  const provider = new authModule.GoogleAuthProvider();
  for (const scope of scopes) {
    provider.addScope(scope);
  }
  const credential = await authModule.signInWithPopup(auth, provider);
  const profile = buildProfile(credential.user, { provider: "google.com" });
  persistSession(profile);
  return profile;
}

/**
 * Local guest session: instant access to the studio with no Firebase account.
 * Guest sessions carry no ID token, so backend integrations stay disabled until
 * the creator signs in with a real account.
 */
export async function signInAsGuest() {
  const profile = {
    uid: `guest-${Date.now().toString(36)}`,
    name: "Creator Guest",
    email: "",
    photoURL: "",
    provider: "guest",
    isGuest: true,
  };
  persistSession(profile);
  return profile;
}

export async function signOut() {
  clearSession();
  if (!isFirebaseConfigured()) return;
  try {
    const { auth, authModule } = await getAuthRuntime();
    await authModule.signOut(auth);
  } catch (_error) {
    // The local session is already cleared; a failed SDK sign-out is harmless.
  }
}

/**
 * Return a fresh Firebase ID token for the signed-in creator, or null when the
 * current session is a guest session or Firebase is unavailable.
 */
export async function getIdToken(forceRefresh = false) {
  const session = getStoredSession();
  if (!session || session.isGuest || !isFirebaseConfigured()) return null;

  try {
    const { auth } = await getAuthRuntime();
    if (typeof auth.authStateReady === "function") {
      await auth.authStateReady();
    }
    const user = auth.currentUser;
    if (!user) return null;
    return await user.getIdToken(forceRefresh);
  } catch (_error) {
    return null;
  }
}

const AUTH_ERROR_MESSAGES = {
  "auth/not-configured":
    "Firebase is not configured. Add the NEXT_PUBLIC_FIREBASE_* variables to the repository root .env.local file.",
  "auth/invalid-email": "That email address is not valid.",
  "auth/missing-password": "Enter your password to continue.",
  "auth/user-not-found": "No account found with that email address.",
  "auth/wrong-password": "Incorrect password. Please try again.",
  "auth/invalid-credential": "Incorrect email or password. Please try again.",
  "auth/invalid-login-credentials": "Incorrect email or password. Please try again.",
  "auth/email-already-in-use": "An account already exists with that email address.",
  "auth/weak-password": "Choose a password with at least 6 characters.",
  "auth/too-many-requests": "Too many attempts. Please wait a moment and try again.",
  "auth/user-disabled": "This account has been disabled.",
  "auth/popup-closed-by-user": "Google sign-in was cancelled.",
  "auth/cancelled-popup-request": "Google sign-in was cancelled.",
  "auth/popup-blocked": "Your browser blocked the sign-in popup. Allow popups and try again.",
  "auth/operation-not-allowed":
    "This sign-in method is not enabled for the Firebase project. Enable it in the Firebase console.",
  "auth/network-request-failed": "Network error. Check your connection and try again.",
  "auth/unauthorized-domain":
    "This domain is not authorised for Firebase sign-in. Add it in the Firebase console.",
};

export function describeAuthError(error) {
  if (!error) return "Authentication failed. Please try again.";
  const code = error.code || "";
  if (AUTH_ERROR_MESSAGES[code]) return AUTH_ERROR_MESSAGES[code];
  if (error.name === "AuthError" && error.message) return error.message;
  return error.message || "Authentication failed. Please try again.";
}
