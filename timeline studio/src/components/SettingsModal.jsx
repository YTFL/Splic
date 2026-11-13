import React, { useState } from "react";
import {
  X,
  Camera,
  Video,
  Share2,
  CheckCircle2,
  Shield,
  Palette,
  Check,
} from "lucide-react";
import { SplicLogo } from "./SplicLogo.jsx";

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

              {/* Instagram */}
              <div className="splic-social-link-card">
                <div className="splic-social-link-left">
                  <div className="splic-social-link-icon" style={{ color: "var(--splic-red-primary)" }}>
                    <Camera size={20} strokeWidth={1.5} />
                  </div>
                  <div>
                    <div className="splic-social-link-title">Instagram Reels</div>
                    <div className="splic-social-link-handle">
                      {socials.instagram.connected ? socials.instagram.handle : "Not connected"}
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
                    style={{ width: "auto", padding: "6px 12px", fontSize: "11px" }}
                    onClick={() => toggleSocial("instagram", "@indic_creator_daily")}
                  >
                    {socials.instagram.connected ? "Disconnect" : "Connect"}
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
                      {socials.youtube.connected ? socials.youtube.handle : "Not connected"}
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
                    style={{ width: "auto", padding: "6px 12px", fontSize: "11px" }}
                    onClick={() => toggleSocial("youtube", "Splic Tech Shorts")}
                  >
                    {socials.youtube.connected ? "Disconnect" : "Connect"}
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
