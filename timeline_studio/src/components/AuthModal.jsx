import React, { useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Globe,
  Video,
  Check,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { SplicLogo, SplicInlaidEmblem } from "./SplicLogo.jsx";
import {
  describeAuthError,
  signInAsGuest,
  signInWithEmail,
  signInWithGoogle,
  signUpWithEmail,
} from "../lib/firebaseAuth.js";

// Read-only YouTube scope requested by the "Continue with YouTube Creator" entry point.
const YOUTUBE_READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly";

export function AuthModal({
  onLogin,
  onClose,
  initialTab = "login", // "login" | "signup"
}) {
  const [tab, setTab] = useState(initialTab);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [rememberMe, setRememberMe] = useState(true);
  const [busyAction, setBusyAction] = useState(""); // "" | "email" | "google" | "youtube" | "guest"
  const [error, setError] = useState("");

  const isBusy = Boolean(busyAction);

  const runAuth = async (action, task) => {
    if (isBusy) return;
    setBusyAction(action);
    setError("");
    try {
      const profile = await task();
      if (onLogin) {
        onLogin(profile);
      }
    } catch (authError) {
      setError(describeAuthError(authError));
    } finally {
      setBusyAction("");
    }
  };

  const handleSubmit = (e) => {
    e?.preventDefault();
    const trimmedEmail = email.trim();
    const trimmedName = name.trim();
    if (!trimmedEmail || !password) {
      setError("Enter your email address and password to continue.");
      return;
    }
    runAuth("email", () => (
      tab === "signup"
        ? signUpWithEmail(trimmedEmail, password, trimmedName)
        : signInWithEmail(trimmedEmail, password)
    ));
  };

  const handleGoogleLogin = () => runAuth("google", () => signInWithGoogle());

  const handleYouTubeLogin = () =>
    runAuth("youtube", () => signInWithGoogle({ scopes: [YOUTUBE_READONLY_SCOPE] }));

  const handleGuestLogin = () => runAuth("guest", () => signInAsGuest());

  return (
    <div className="splic-auth-page">
      {/* Top Bar with Home navigation */}
      <header className="splic-auth-page-topbar">
        <div className="splic-auth-page-topbar-inner">
          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            <SplicLogo size={28} showText={true} />
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            {onClose && (
              <button
                type="button"
                className="splic-btn-ghost-nav"
                onClick={onClose}
              >
                <ArrowLeft size={14} strokeWidth={1.5} />
                <span>Back to Home</span>
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="splic-auth-page-main">
        <div className="splic-auth-page-container">
          {/* Left Brand Showcase Column */}
          <div className="splic-auth-brand-col">
            <h1 className="splic-auth-hero-title">
              Sign In to <span>Splic Studio</span>
            </h1>

            <p className="splic-auth-hero-subtitle">
              Multi-track timeline editing, Romanized Indic captions, and high-performance video export in your browser.
            </p>

            {/* Inlayed Animated Vector Logo — No black container */}
            <div className="splic-auth-logo-inlay">
              <SplicInlaidEmblem size={250} showText={false} />
            </div>

            {/* Feature Bullets */}
            <div className="splic-auth-features-list">
              <div className="splic-auth-feature-row">
                <div className="splic-auth-feature-check">
                  <Check size={13} strokeWidth={2.5} />
                </div>
                <span>Phonetic Romanized Indic subtitles & styling</span>
              </div>
              <div className="splic-auth-feature-row">
                <div className="splic-auth-feature-check">
                  <Check size={13} strokeWidth={2.5} />
                </div>
                <span>Automatic ripple cuts and timeline pause removal</span>
              </div>
              <div className="splic-auth-feature-row">
                <div className="splic-auth-feature-check">
                  <Check size={13} strokeWidth={2.5} />
                </div>
                <span>Hardware-accelerated 9:16 export & social publishing</span>
              </div>
            </div>
          </div>

          {/* Right Isolated Auth Card */}
          <div className="splic-auth-card-col">
            <div className="splic-auth-isolated-card">
              {/* Tab Switcher */}
              <div className="splic-auth-tabs">
                <button
                  type="button"
                  className={`splic-auth-tab ${tab === "login" ? "is-active" : ""}`}
                  onClick={() => setTab("login")}
                >
                  Sign In
                </button>
                <button
                  type="button"
                  className={`splic-auth-tab ${tab === "signup" ? "is-active" : ""}`}
                  onClick={() => setTab("signup")}
                >
                  Create Account
                </button>
              </div>

              {/* Social Logins */}
              <div className="splic-social-login-group">
                <button
                  type="button"
                  className="splic-social-btn"
                  onClick={handleGoogleLogin}
                  disabled={isBusy}
                >
                  {busyAction === "google" ? (
                    <Loader2 size={16} strokeWidth={1.5} className="spin-icon" />
                  ) : (
                    <Globe size={16} strokeWidth={1.5} />
                  )}
                  <span>Continue with Google</span>
                </button>
                <button
                  type="button"
                  className="splic-social-btn"
                  onClick={handleYouTubeLogin}
                  disabled={isBusy}
                >
                  {busyAction === "youtube" ? (
                    <Loader2 size={16} strokeWidth={1.5} className="spin-icon" />
                  ) : (
                    <Video size={16} strokeWidth={1.5} style={{ color: "var(--splic-red-primary)" }} />
                  )}
                  <span>Continue with YouTube Creator</span>
                </button>
              </div>

              {error ? (
                <div
                  role="alert"
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "8px",
                    background: "rgba(225, 29, 72, 0.12)",
                    border: "1px solid rgba(225, 29, 72, 0.35)",
                    borderRadius: "8px",
                    padding: "10px 12px",
                    marginBottom: "14px",
                    fontSize: "12px",
                    lineHeight: 1.45,
                    color: "#fda4af",
                  }}
                >
                  <AlertCircle size={14} strokeWidth={1.5} style={{ flexShrink: 0, marginTop: "1px" }} />
                  <span>{error}</span>
                </div>
              ) : null}

              <div className="splic-auth-divider">
                <span>Or sign in with email</span>
              </div>

              {/* Email & Password Form */}
              <form onSubmit={handleSubmit}>
                {tab === "signup" && (
                  <div className="splic-form-group">
                    <label>Creator Name</label>
                    <input
                      type="text"
                      className="splic-form-input"
                      placeholder="e.g. Shashank Kumar"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                    />
                  </div>
                )}

                <div className="splic-form-group">
                  <label>Work Email</label>
                  <input
                    type="email"
                    className="splic-form-input"
                    placeholder="creator@splic.ai"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>

                <div className="splic-form-group">
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <label>Password</label>
                    {tab === "login" && (
                      <button
                        type="button"
                        style={{
                          background: "none",
                          border: "none",
                          color: "var(--splic-text-muted)",
                          fontSize: "11px",
                          cursor: "pointer",
                        }}
                      >
                        Forgot?
                      </button>
                    )}
                  </div>
                  <input
                    type="password"
                    className="splic-form-input"
                    placeholder="Enter password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "8px", margin: "14px 0 20px 0" }}>
                  <input
                    type="checkbox"
                    id="splic-remember"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    style={{ accentColor: "var(--splic-red-primary)" }}
                  />
                  <label htmlFor="splic-remember" style={{ fontSize: "12px", color: "var(--splic-text-muted)", cursor: "pointer" }}>
                    Keep me signed in on this workstation
                  </label>
                </div>

                <button
                  type="submit"
                  className="splic-btn-primary"
                  style={{ width: "100%", padding: "12px", fontSize: "13px" }}
                  disabled={isBusy}
                >
                  {busyAction === "email" ? (
                    <>
                      <Loader2 size={15} strokeWidth={2} className="spin-icon" />
                      <span>{tab === "login" ? "Signing In…" : "Creating Account…"}</span>
                    </>
                  ) : (
                    <>
                      <span>{tab === "login" ? "Sign In to Projects" : "Create Account & Launch Studio"}</span>
                      <ArrowRight size={15} strokeWidth={2} />
                    </>
                  )}
                </button>
              </form>

              {/* Guest / Direct access link */}
              <div style={{ marginTop: "20px", textAlign: "center" }}>
                <button
                  type="button"
                  onClick={handleGuestLogin}
                  disabled={isBusy}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--splic-text-muted)",
                    fontSize: "12px",
                    cursor: isBusy ? "default" : "pointer",
                    textDecoration: "underline",
                  }}
                >
                  {busyAction === "guest" ? "Preparing guest session…" : "Continue as Guest (Instant Access)"}
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
