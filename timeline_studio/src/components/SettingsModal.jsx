import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  X,
  Camera,
  Video,
  Share2,
  CheckCircle2,
  Shield,
  Palette,
  Check,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { SplicLogo } from "./SplicLogo.jsx";
import { isSignedIn } from "../lib/firebaseAuth.js";
import {
  OAUTH_MESSAGE_TYPE,
  buildOAuthCallbackUrl,
  disconnectAccount,
  getConnectedAccounts,
  initiateInstagramConnect,
  initiateYouTubeConnect,
  mapAccountsToSocialState,
  openOAuthPopup,
} from "../lib/composioClient.js";

const noticeStyle = {
  display: "flex",
  alignItems: "center",
  gap: "8px",
  background: "rgba(148, 163, 184, 0.08)",
  border: "1px solid var(--splic-border-subtle)",
  borderRadius: "8px",
  padding: "10px 12px",
  marginBottom: "14px",
  fontSize: "12px",
  color: "var(--splic-text-muted)",
};

const errorStyle = {
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
};

export function SettingsModal({
  isOpen = true,
  onClose,
  connectedSocials,
  onUpdateSocials,
  user: _user,
  onUpdateUser: _onUpdateUser,
}) {
  const [activeTab, setActiveTab] = useState("social"); // "social" | "workspace" | "general"
  const [socials, setSocials] = useState(
    connectedSocials || {
      instagram: { connected: true, handle: "@indic_creator_daily", name: "Instagram Reels" },
      youtube: { connected: true, handle: "Splic Tech Shorts", name: "YouTube Shorts & Video" },
      tiktok: { connected: false, handle: "", name: "TikTok Creator" },
      x: { connected: false, handle: "", name: "X (Twitter)" },
    }
  );

  const [defaultFps, setDefaultFps] = useState("30");
  const [autoRipple, setAutoRipple] = useState(true);
  const [snapPlayhead, setSnapPlayhead] = useState(true);
  const [savedToast, setSavedToast] = useState(false);

  // Live Composio account state for the Instagram and YouTube cards.
  const socialsRef = useRef(socials);
  socialsRef.current = socials;
  const [remoteStatus, setRemoteStatus] = useState("idle"); // idle | loading | signed-out | ready | awaiting-authorization | error
  const [remoteError, setRemoteError] = useState("");
  const [busyPlatform, setBusyPlatform] = useState("");

  const refreshAccounts = useCallback(async () => {
    if (!isSignedIn()) {
      setRemoteStatus("signed-out");
      return;
    }
    setRemoteStatus("loading");
    setRemoteError("");
    try {
      const result = await getConnectedAccounts();
      const next = mapAccountsToSocialState(result?.accounts || [], socialsRef.current);
      setSocials(next);
      if (onUpdateSocials) onUpdateSocials(next);
      setRemoteStatus("ready");
    } catch (error) {
      setRemoteStatus("error");
      setRemoteError(error?.message || "Could not load your connected accounts.");
    }
  }, [onUpdateSocials]);

  useEffect(() => {
    if (!isOpen) return;
    refreshAccounts();
  }, [isOpen, refreshAccounts]);

  useEffect(() => {
    if (!isOpen) return undefined;
    const handleOAuthMessage = (event) => {
      if (event.origin !== window.location.origin) return;
      if (event.data?.type !== OAUTH_MESSAGE_TYPE) return;
      refreshAccounts();
    };
    window.addEventListener("message", handleOAuthMessage);
    return () => window.removeEventListener("message", handleOAuthMessage);
  }, [isOpen, refreshAccounts]);

  const connectPlatform = async (platform) => {
    setBusyPlatform(platform);
    setRemoteError("");
    try {
      const callbackUrl = buildOAuthCallbackUrl(platform);
      const result = platform === "instagram"
        ? await initiateInstagramConnect(callbackUrl)
        : await initiateYouTubeConnect(callbackUrl);
      if (!result?.redirect_url) {
        throw new Error("The backend did not return an authorization link for this platform.");
      }
      const popup = openOAuthPopup(result.redirect_url);
      if (!popup) {
        throw new Error("Your browser blocked the authorization popup. Allow popups and try again.");
      }
      setRemoteStatus("awaiting-authorization");
    } catch (error) {
      setRemoteStatus("error");
      setRemoteError(error?.message || "Could not start the authorization flow.");
    } finally {
      setBusyPlatform("");
    }
  };

  const disconnectPlatform = async (platform) => {
    const accountId = socialsRef.current?.[platform]?.accountId;
    if (!accountId) {
      const fallback = { ...socialsRef.current };
      fallback[platform] = { ...fallback[platform], connected: false, handle: "", accountId: "" };
      setSocials(fallback);
      if (onUpdateSocials) onUpdateSocials(fallback);
      return;
    }
    setBusyPlatform(platform);
    setRemoteError("");
    try {
      await disconnectAccount(accountId);
      await refreshAccounts();
    } catch (error) {
      setRemoteStatus("error");
      setRemoteError(error?.message || "Could not disconnect that account.");
    } finally {
      setBusyPlatform("");
    }
  };

  if (!isOpen) return null;

  const toggleSocial = (platformKey, defaultHandle) => {
    const current = socials[platformKey];
    const updated = {
      ...socials,
      [platformKey]: {
        ...current,
        connected: !current.connected,
        handle: !current.connected ? (current.handle || defaultHandle) : "",
      },
    };
    setSocials(updated);
    if (onUpdateSocials) {
      onUpdateSocials(updated);
    }
  };

  const handleSave = () => {
    setSavedToast(true);
    setTimeout(() => {
      setSavedToast(false);
      if (onClose) onClose();
    }, 900);
  };

  return (
    <div className="splic-modal-overlay">
      <div className="splic-settings-modal">
        {/* Header */}
        <div className="splic-settings-header">
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <SplicLogo size={26} showText={false} />
            <div>
              <h2 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "var(--splic-text-bright)" }}>
                Studio Settings & Integrations
              </h2>
              <span style={{ fontSize: "11px", color: "var(--splic-text-muted)" }}>
                Manage connected platforms, timeline rules & workspace preferences
              </span>
            </div>
          </div>

          <button
            type="button"
            className="splic-auth-close-btn"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={18} strokeWidth={1.5} />
          </button>
        </div>

        {/* Tab navigation */}
        <div style={{ padding: "0 28px", borderBottom: "1px solid var(--splic-border-subtle)" }}>
          <div style={{ display: "flex", gap: "16px" }}>
            <button
              type="button"
              className={`splic-auth-tab ${activeTab === "social" ? "is-active" : ""}`}
              style={{
                borderRadius: "0",
                borderBottom: activeTab === "social" ? "2px solid var(--splic-red-primary)" : "2px solid transparent",
                background: "none",
                padding: "12px 6px",
              }}
              onClick={() => setActiveTab("social")}
            >
              Connected Socials
            </button>
            <button
              type="button"
              className={`splic-auth-tab ${activeTab === "workspace" ? "is-active" : ""}`}
              style={{
                borderRadius: "0",
                borderBottom: activeTab === "workspace" ? "2px solid var(--splic-red-primary)" : "2px solid transparent",
                background: "none",
                padding: "12px 6px",
              }}
              onClick={() => setActiveTab("workspace")}
            >
              Timeline & Editing
            </button>
            <button
              type="button"
              className={`splic-auth-tab ${activeTab === "general" ? "is-active" : ""}`}
              style={{
                borderRadius: "0",
                borderBottom: activeTab === "general" ? "2px solid var(--splic-red-primary)" : "2px solid transparent",
                background: "none",
                padding: "12px 6px",
              }}
              onClick={() => setActiveTab("general")}
            >
              Theme & Hardware
            </button>
          </div>
        </div>

        {/* Settings Body */}
        <div className="splic-settings-body">
          {/* TAB 1: SOCIAL PLATFORMS */}
          {activeTab === "social" && (
            <>
              <div>
                <h3 style={{ margin: "0 0 4px 0", fontSize: "14px", fontWeight: 700, color: "var(--splic-text-bright)" }}>
                  Link Social Media Platforms
                </h3>
                <p style={{ margin: "0 0 16px 0", fontSize: "12px", color: "var(--splic-text-muted)" }}>
                  Connect your creator accounts for direct 1-click video publishing from the Export workspace.
                </p>
              </div>

              {remoteStatus === "signed-out" ? (
                <div style={noticeStyle}>
                  <AlertCircle size={14} strokeWidth={1.5} />
                  <span>Sign in with a Splic account to link Instagram or YouTube.</span>
                </div>
              ) : null}

              {remoteStatus === "awaiting-authorization" ? (
                <div style={noticeStyle}>
                  <Loader2 size={14} strokeWidth={1.5} className="spin-icon" />
                  <span>Complete the authorization in the popup window. This panel refreshes automatically.</span>
                </div>
              ) : null}

              {remoteError ? (
                <div style={errorStyle} role="alert">
                  <AlertCircle size={14} strokeWidth={1.5} style={{ flexShrink: 0, marginTop: "1px" }} />
                  <span>{remoteError}</span>
                </div>
              ) : null}

              {/* Instagram */}
              <div className="splic-social-link-card">
                <div className="splic-social-link-left">
                  <div className="splic-social-link-icon" style={{ color: "var(--splic-red-primary)" }}>
                    <Camera size={20} strokeWidth={1.5} />
                  </div>
                  <div>
                    <div className="splic-social-link-title">Instagram Reels</div>
                    <div className="splic-social-link-handle">
                      {socials.instagram.connected
                        ? socials.instagram.handle || "Connected account"
                        : "Not connected"}
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span className={`splic-link-status-badge ${socials.instagram.connected ? "is-connected" : "is-disconnected"}`}>
                    {socials.instagram.connected && <Check size={11} strokeWidth={2} />}
                    {socials.instagram.connected ? "Connected" : "Disconnected"}
                  </span>
                  <button
                    type="button"
                    className="splic-btn-secondary"
                    style={{ width: "auto", padding: "6px 12px", fontSize: "11px", display: "inline-flex", alignItems: "center", gap: "6px" }}
                    disabled={busyPlatform === "instagram"}
                    onClick={() => (
                      socials.instagram.connected
                        ? disconnectPlatform("instagram")
                        : connectPlatform("instagram")
                    )}
                  >
                    {busyPlatform === "instagram" ? (
                      <>
                        <Loader2 size={12} strokeWidth={1.5} className="spin-icon" />
                        <span>Working</span>
                      </>
                    ) : (
                      <span>{socials.instagram.connected ? "Disconnect" : "Connect"}</span>
                    )}
                  </button>
                </div>
              </div>

              {/* YouTube */}
              <div className="splic-social-link-card">
                <div className="splic-social-link-left">
                  <div className="splic-social-link-icon" style={{ color: "var(--splic-red-primary)" }}>
                    <Video size={20} strokeWidth={1.5} />
                  </div>
                  <div>
                    <div className="splic-social-link-title">YouTube Shorts & Channel</div>
                    <div className="splic-social-link-handle">
                      {socials.youtube.connected
                        ? socials.youtube.handle || "Connected account"
                        : "Not connected"}
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span className={`splic-link-status-badge ${socials.youtube.connected ? "is-connected" : "is-disconnected"}`}>
                    {socials.youtube.connected && <Check size={11} strokeWidth={2} />}
                    {socials.youtube.connected ? "Connected" : "Disconnected"}
                  </span>
                  <button
                    type="button"
                    className="splic-btn-secondary"
                    style={{ width: "auto", padding: "6px 12px", fontSize: "11px", display: "inline-flex", alignItems: "center", gap: "6px" }}
                    disabled={busyPlatform === "youtube"}
                    onClick={() => (
                      socials.youtube.connected
                        ? disconnectPlatform("youtube")
                        : connectPlatform("youtube")
                    )}
                  >
                    {busyPlatform === "youtube" ? (
                      <>
                        <Loader2 size={12} strokeWidth={1.5} className="spin-icon" />
                        <span>Working</span>
                      </>
                    ) : (
                      <span>{socials.youtube.connected ? "Disconnect" : "Connect"}</span>
                    )}
                  </button>
                </div>
              </div>

              {/* TikTok */}
              <div className="splic-social-link-card">
                <div className="splic-social-link-left">
                  <div className="splic-social-link-icon">
                    <Share2 size={20} strokeWidth={1.5} />
                  </div>
                  <div>
                    <div className="splic-social-link-title">TikTok Creator Feed</div>
                    <div className="splic-social-link-handle">
                      {socials.tiktok.connected ? socials.tiktok.handle : "Not connected"}
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span className={`splic-link-status-badge ${socials.tiktok.connected ? "is-connected" : "is-disconnected"}`}>
                    {socials.tiktok.connected && <Check size={11} strokeWidth={2} />}
                    {socials.tiktok.connected ? "Connected" : "Disconnected"}
                  </span>
                  <button
                    type="button"
                    className="splic-btn-secondary"
                    style={{ width: "auto", padding: "6px 12px", fontSize: "11px" }}
                    onClick={() => toggleSocial("tiktok", "@splic_shortform")}
                  >
                    {socials.tiktok.connected ? "Disconnect" : "Connect"}
                  </button>
                </div>
              </div>

              {/* X / Twitter */}
              <div className="splic-social-link-card">
                <div className="splic-social-link-left">
                  <div className="splic-social-link-icon">
                    <Share2 size={20} strokeWidth={1.5} />
                  </div>
                  <div>
                    <div className="splic-social-link-title">X (Twitter Video)</div>
                    <div className="splic-social-link-handle">
                      {socials.x.connected ? socials.x.handle : "Not connected"}
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span className={`splic-link-status-badge ${socials.x.connected ? "is-connected" : "is-disconnected"}`}>
                    {socials.x.connected && <Check size={11} strokeWidth={2} />}
                    {socials.x.connected ? "Connected" : "Disconnected"}
                  </span>
                  <button
                    type="button"
                    className="splic-btn-secondary"
                    style={{ width: "auto", padding: "6px 12px", fontSize: "11px" }}
                    onClick={() => toggleSocial("x", "@splic_editor")}
                  >
                    {socials.x.connected ? "Disconnect" : "Connect"}
                  </button>
                </div>
              </div>
            </>
          )}

          {/* TAB 2: WORKSPACE & TIMELINE */}
          {activeTab === "workspace" && (
            <>
              <div>
                <h3 style={{ margin: "0 0 4px 0", fontSize: "14px", fontWeight: 700, color: "var(--splic-text-bright)" }}>
                  Timeline & Editing Rules
                </h3>
                <p style={{ margin: "0 0 16px 0", fontSize: "12px", color: "var(--splic-text-muted)" }}>
                  Default behavior for ripple cuts, frame rates, and magnetic snapping.
                </p>
              </div>

              <div className="splic-social-link-card">
                <div>
                  <div className="splic-social-link-title">Default Frame Rate</div>
                  <div className="splic-social-link-sub" style={{ fontSize: "11px", color: "var(--splic-text-muted)" }}>
                    Standard output frequency for timeline clips and canvas preview
                  </div>
                </div>
                <select
                  value={defaultFps}
                  onChange={(e) => setDefaultFps(e.target.value)}
                  className="splic-form-input"
                  style={{ width: "100px", padding: "6px 10px" }}
                >
                  <option value="24">24 FPS</option>
                  <option value="30">30 FPS</option>
                  <option value="60">60 FPS</option>
                </select>
              </div>

              <div className="splic-social-link-card">
                <div>
                  <div className="splic-social-link-title">Automatic Ripple Cuts</div>
                  <div className="splic-social-link-sub" style={{ fontSize: "11px", color: "var(--splic-text-muted)" }}>
                    Close dead-air gaps automatically when cutting filler words
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={autoRipple}
                  onChange={(e) => setAutoRipple(e.target.checked)}
                  style={{ accentColor: "var(--splic-red-primary)", width: "18px", height: "18px", cursor: "pointer" }}
                />
              </div>

              <div className="splic-social-link-card">
                <div>
                  <div className="splic-social-link-title">Magnetic Playhead Snapping</div>
                  <div className="splic-social-link-sub" style={{ fontSize: "11px", color: "var(--splic-text-muted)" }}>
                    Snap playhead to clip boundaries, caption timestamps, and audio cues
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={snapPlayhead}
                  onChange={(e) => setSnapPlayhead(e.target.checked)}
                  style={{ accentColor: "var(--splic-red-primary)", width: "18px", height: "18px", cursor: "pointer" }}
                />
              </div>
            </>
          )}

          {/* TAB 3: THEME & WORKSPACE */}
          {activeTab === "general" && (
            <>
              <div>
                <h3 style={{ margin: "0 0 4px 0", fontSize: "14px", fontWeight: 700, color: "var(--splic-text-bright)" }}>
                  Theme & Hardware Acceleration
                </h3>
                <p style={{ margin: "0 0 16px 0", fontSize: "12px", color: "var(--splic-text-muted)" }}>
                  Active aesthetic profile & system capabilities
                </p>
              </div>

              <div className="splic-social-link-card">
                <div className="splic-social-link-left">
                  <div className="splic-social-link-icon" style={{ color: "var(--splic-red-primary)" }}>
                    <Palette size={20} strokeWidth={1.5} />
                  </div>
                  <div>
                    <div className="splic-social-link-title">Dark Charcoal & Crimson Red</div>
                    <div className="splic-social-link-handle">Matte luxury aesthetic • Zero bloom / zero tacky glow</div>
                  </div>
                </div>
                <span className="splic-link-status-badge is-connected">
                  <Check size={11} strokeWidth={2} /> Active
                </span>
              </div>

              <div className="splic-social-link-card">
                <div className="splic-social-link-left">
                  <div className="splic-social-link-icon" style={{ color: "#4ade80" }}>
                    <Shield size={20} strokeWidth={1.5} />
                  </div>
                  <div>
                    <div className="splic-social-link-title">WebCodecs GPU Acceleration</div>
                    <div className="splic-social-link-handle">COOP & COEP isolated SharedArrayBuffer</div>
                  </div>
                </div>
                <span className="splic-link-status-badge is-connected">
                  <Check size={11} strokeWidth={2} /> Supported
                </span>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div style={{ padding: "16px 28px", borderTop: "1px solid var(--splic-border-subtle)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          {savedToast ? (
            <span style={{ fontSize: "12px", color: "#4ade80", display: "flex", alignItems: "center", gap: "6px" }}>
              <CheckCircle2 size={14} strokeWidth={2} />
              Settings saved successfully!
            </span>
          ) : (
            <span />
          )}

          <div style={{ display: "flex", gap: "10px" }}>
            <button
              type="button"
              className="splic-btn-secondary"
              style={{ width: "auto", padding: "8px 16px" }}
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              type="button"
              className="splic-btn-primary"
              style={{ width: "auto", padding: "8px 22px" }}
              onClick={handleSave}
            >
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
