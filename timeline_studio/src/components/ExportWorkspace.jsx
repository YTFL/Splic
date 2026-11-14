import React, { useRef, useState } from "react";
import {
  Download,
  Share2,
  Film,
  Sparkles,
  Sliders,
  CheckCircle2,
  Clock,
  HardDrive,
  Eye,
  RefreshCw,
  Video,
  FileVideo,
  Check,
  Camera,
  Radio,
  Layers,
  AlertCircle,
  ExternalLink,
} from "lucide-react";
import { publishToInstagram, publishToYouTube } from "../lib/composioClient.js";

export function ExportWorkspace({
  timelineDuration = 10,
  exportSettings,
  setExportSettings,
  onExportVideo,
  exporting = false,
  exportPercent = 0,
  exportPhase = "",
  exportError = null,
  onCancelExport,
  ratioId = "9:16",
  previewCanvasRef,
  previewVideoRef,
  connectedSocials,
  onOpenSettings,
  t = (k, fallback) => fallback || k,
}) {
  const [selectedPreset, setSelectedPreset] = useState("instagram-reels");
  const [socialPlatform, setSocialPlatform] = useState("instagram");
  const [videoTitle, setVideoTitle] = useState("My Reel — Splic Studio");
  const [videoDescription, setVideoDescription] = useState(
    "Created with Splic Studio #AutoCut #SarvamAI #Reels #IndicCreators"
  );
  const [tags, setTags] = useState("reel, viral, sarvam, hinglish, ai");
  const [privacy, setPrivacy] = useState("public");
  const [qualityPreset, setQualityPreset] = useState("high");
  const [burnCaptions, setBurnCaptions] = useState(true);
  const [socialUploadState, setSocialUploadState] = useState("idle"); // "idle" | "rendering" | "uploading" | "success"
  const [publishError, setPublishError] = useState("");
  const [publishedResult, setPublishedResult] = useState(null);
  const exportedArtifactRef = useRef(null);
  const publishing = socialUploadState === "rendering" || socialUploadState === "uploading";
  // A cached render is only reusable while the encoding settings are unchanged.
  const renderSignature = `${selectedPreset}|${qualityPreset}|${burnCaptions ? "captions" : "clean"}`;

  const platformSocial = connectedSocials?.[socialPlatform] || { connected: false, handle: "" };
  const isSelectedPlatformConnected = Boolean(platformSocial.connected);
  const platformLabel = socialPlatform === "instagram" ? "Instagram" : "YouTube";

  const presets = [
    {
      id: "instagram-reels",
      name: "Instagram Reels",
      format: "9:16 Vertical",
      resolution: "1080 × 1920",
      fps: "30 / 60 FPS",
      bitrate: "12 Mbps (H.264)",
      badge: "Reels / Stories",
      recommended: true,
    },
    {
      id: "youtube-shorts",
      name: "YouTube Shorts",
      format: "9:16 Vertical",
      resolution: "1080 × 1920",
      fps: "60 FPS",
      bitrate: "15 Mbps (H.264)",
      badge: "Shorts Feed",
      recommended: false,
    },
    {
      id: "youtube-hd",
      name: "YouTube 16:9 HD",
      format: "16:9 Landscape",
      resolution: "1920 × 1080",
      fps: "30 / 60 FPS",
      bitrate: "16 Mbps (H.264)",
      badge: "Full HD",
      recommended: false,
    },
    {
      id: "custom-pro",
      name: "Lossless Master",
      format: "NLE Master",
      resolution: "Native Source",
      fps: "Project FPS",
      bitrate: "Pro Quality",
      badge: "Master",
      recommended: false,
    },
  ];

  const handleStartExport = async () => {
    if (!onExportVideo) return;
    const result = await onExportVideo({
      preset: selectedPreset,
      quality: qualityPreset,
      burnCaptions,
    });
    if (result?.status === "success" && result.blob) {
      exportedArtifactRef.current = { artifact: result, signature: renderSignature };
    }
  };

  // Publishing needs the rendered file, so render first when nothing is cached yet.
  const ensureRenderedReel = async () => {
    if (exporting) {
      throw new Error("A render is already running. Wait for it to finish, then publish.");
    }

    const cached = exportedArtifactRef.current;
    if (cached?.signature === renderSignature && cached.artifact?.blob) {
      return cached.artifact;
    }

    if (!onExportVideo) {
      throw new Error("Rendering is not available in this workspace.");
    }

    setSocialUploadState("rendering");
    const result = await onExportVideo({
      preset: selectedPreset,
      quality: qualityPreset,
      burnCaptions,
    });

    if (result?.status === "success" && result.blob) {
      exportedArtifactRef.current = { artifact: result, signature: renderSignature };
      return result;
    }
    if (result?.status === "busy") {
      throw new Error("A render is already running. Wait for it to finish, then publish.");
    }
    if (result?.status === "canceled") {
      throw new Error("The render was cancelled before it could be published.");
    }
    throw new Error(
      result?.error || "The reel could not be rendered. Check the export settings and try again.",
    );
  };

  const handleSocialPublish = async () => {
    if (publishing) return;
    setPublishError("");
    setPublishedResult(null);
    try {
      const artifact = await ensureRenderedReel();
      setSocialUploadState("uploading");

      const result = socialPlatform === "instagram"
        ? await publishToInstagram({
            file: artifact.blob,
            fileName: artifact.fileName,
            caption: [videoTitle, videoDescription].filter(Boolean).join("\n\n"),
            shareToFeed: true,
            accountId: platformSocial.accountId,
          })
        : await publishToYouTube({
            file: artifact.blob,
            fileName: artifact.fileName,
            title: videoTitle,
            description: videoDescription,
            tags: tags.split(",").map((tag) => tag.trim()).filter(Boolean),
            privacy,
            accountId: platformSocial.accountId,
          });

      setPublishedResult(result || null);
      setSocialUploadState("success");
    } catch (error) {
      setSocialUploadState("idle");
      setPublishError(error?.message || "Publishing failed. Please try again.");
    }
  };

  const estimatedSizeMB = Math.max(
    2.5,
    ((timelineDuration * (qualityPreset === "high" ? 12 : 8)) / 8).toFixed(1)
  );

  return (
    <div className="davinci-export-screen">
      {/* Top Deliver Header */}
      <header className="davinci-deliver-header">
        <div className="deliver-header-left">
          <Film size={18} strokeWidth={1.25} style={{ color: "var(--splic-red-primary)" }} />
          <h2 className="deliver-header-title">Deliver & Social Publish</h2>
        </div>

        <div className="deliver-header-stats">
          <div className="deliver-stat-pill">
            <Clock size={13} strokeWidth={1.25} />
            <span>Timeline: {timelineDuration.toFixed(1)}s</span>
          </div>
          <div className="deliver-stat-pill">
            <HardDrive size={13} strokeWidth={1.25} />
            <span>Est. Size: ~{estimatedSizeMB} MB</span>
          </div>
          <div className="deliver-stat-pill">
            <Layers size={13} strokeWidth={1.25} />
            <span>Format: {ratioId}</span>
          </div>
        </div>
      </header>

      {/* Main Deliver Grid */}
      <div className="davinci-deliver-grid">
        {/* Left: Render Settings & Format Presets */}
        <section className="deliver-panel">
          <div className="deliver-panel-title">
            <FileVideo size={16} strokeWidth={1.25} style={{ color: "var(--splic-red-primary)" }} />
            <span>Export Format Presets</span>
          </div>

          <div className="deliver-panel-body">
            <div className="deliver-preset-cards">
              {presets.map((preset) => {
                const isSelected = selectedPreset === preset.id;
                return (
                  <div
                    key={preset.id}
                    className={`deliver-preset-card ${isSelected ? "is-selected" : ""}`}
                    onClick={() => setSelectedPreset(preset.id)}
                  >
                    <div className="preset-card-top">
                      <span className="preset-card-name">{preset.name}</span>
                      {preset.recommended && (
                        <span className="preset-rec-tag">Recommended</span>
                      )}
                    </div>
                    <div className="preset-card-details">
                      <span className="preset-res">{preset.resolution}</span>
                      <span className="preset-spec">
                        {preset.format} • {preset.bitrate}
                      </span>
                    </div>
                    {isSelected && (
                      <div className="preset-selected-check">
                        <Check size={14} strokeWidth={2} />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            <div style={{ marginTop: "4px" }}>
              <div className="deliver-panel-title" style={{ fontSize: "12px", marginBottom: "12px" }}>
                <Sliders size={14} strokeWidth={1.25} style={{ color: "var(--splic-red-primary)" }} />
                <span>Encoding Parameters</span>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <label style={{ fontSize: "12px", color: "var(--splic-text-subtle)" }}>Quality Target</label>
                  <div className="deliver-segmented-pill" style={{ width: "180px", height: "32px" }}>
                    {["balanced", "high", "master"].map((q) => (
                      <button
                        key={q}
                        type="button"
                        className={`seg-pill-btn ${qualityPreset === q ? "is-active" : ""}`}
                        onClick={() => setQualityPreset(q)}
                      >
                        {q.charAt(0).toUpperCase() + q.slice(1)}
                      </button>
                    ))}
                  </div>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <label style={{ fontSize: "12px", color: "var(--splic-text-subtle)" }}>
                    Burn Romanized Karaoke Subtitles
                  </label>
                  <input
                    type="checkbox"
                    checked={burnCaptions}
                    onChange={(e) => setBurnCaptions(e.target.checked)}
                    style={{ accentColor: "var(--splic-red-primary)", width: "16px", height: "16px", cursor: "pointer" }}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="deliver-panel-footer">
            <button
              type="button"
              className="deliver-primary-btn"
              disabled={exporting}
              onClick={handleStartExport}
            >
              {exporting ? (
                <>
                  <RefreshCw size={15} className="spin-icon" strokeWidth={1.5} />
                  <span>Encoding {exportPercent > 0 ? `${exportPercent}%` : "..."}</span>
                </>
              ) : (
                <>
                  <Download size={15} strokeWidth={1.5} />
                  <span>Export Hardware MP4</span>
                </>
              )}
            </button>
          </div>
        </section>

        {/* Center: Live Composition Master Preview */}
        <section className="deliver-panel">
          <div className="deliver-panel-title">
            <Eye size={16} strokeWidth={1.25} style={{ color: "var(--splic-red-primary)" }} />
            <span>Master Output Stage</span>
          </div>

          <div className="deliver-panel-body deliver-preview-body" style={{ alignItems: "center", justifyContent: "center" }}>
            <div
              style={{
                width: "100%",
                height: "100%",
                background: "#08090b",
                borderRadius: "8px",
                border: "1px solid var(--splic-border-subtle)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                position: "relative",
                overflow: "hidden",
                minHeight: "320px",
              }}
            >
              {/* Aspect ratio frame box */}
              <div
                style={{
                  width: ratioId === "16:9" ? "80%" : "220px",
                  height: ratioId === "16:9" ? "200px" : "360px",
                  background: "#0d0e12",
                  border: "1.5px solid var(--splic-border-strong)",
                  borderRadius: "6px",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  position: "relative",
                }}
              >
                <Video size={36} strokeWidth={1.25} style={{ color: "var(--splic-text-muted)", marginBottom: "10px" }} />
                <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--splic-text-bright)" }}>
                  Canvas Preview ({ratioId})
                </span>
                <span style={{ fontSize: "11px", color: "var(--splic-text-muted)", marginTop: "4px" }}>
                  1080p WebCodecs Render Source
                </span>
              </div>

              {/* Rendering Progress Overlay */}
              {exporting && (
                <div
                  style={{
                    position: "absolute",
                    bottom: "20px",
                    left: "24px",
                    right: "24px",
                    background: "rgba(16, 18, 23, 0.95)",
                    border: "1px solid var(--splic-border-strong)",
                    borderRadius: "8px",
                    padding: "16px 20px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px", fontSize: "12px" }}>
                    <span style={{ color: "var(--splic-text-bright)", fontWeight: 600 }}>
                      {exportPhase || "Encoding Frames via WebCodecs..."}
                    </span>
                    <span style={{ color: "var(--splic-red-primary)", fontWeight: 700 }}>
                      {exportPercent}%
                    </span>
                  </div>

                  <div
                    style={{
                      width: "100%",
                      height: "6px",
                      background: "var(--splic-bg-surface)",
                      borderRadius: "3px",
                      overflow: "hidden",
                      marginBottom: "10px",
                    }}
                  >
                    <div
                      style={{
                        width: `${exportPercent}%`,
                        height: "100%",
                        background: "var(--splic-red-primary)",
                        transition: "width 0.2s ease",
                      }}
                    />
                  </div>

                  {onCancelExport && (
                    <button
                      type="button"
                      onClick={onCancelExport}
                      style={{
                        background: "none",
                        border: "none",
                        color: "var(--splic-text-muted)",
                        fontSize: "11px",
                        cursor: "pointer",
                        textDecoration: "underline",
                      }}
                    >
                      Cancel Render
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="deliver-panel-footer deliver-preview-footer">
            <div className="deliver-preview-spec-bar">
              <span>WebCodecs Acceleration</span>
              <span className="deliver-divider">•</span>
              <span>H.264 / AAC High-Profile</span>
              <span className="deliver-divider">•</span>
              <span>1080p Master Output</span>
            </div>
          </div>
        </section>

        {/* Right: 1-Click Social Media Upload */}
        <section className="deliver-panel">
          <div className="deliver-panel-title">
            <Share2 size={16} strokeWidth={1.25} style={{ color: "var(--splic-red-primary)" }} />
            <span>1-Click Social Media Publish</span>
          </div>

          <div className="deliver-panel-body">
            {/* Social Platform Toggle */}
            <div className="deliver-segmented-pill" style={{ height: "36px" }}>
              <button
                type="button"
                className={`seg-pill-btn ${socialPlatform === "instagram" ? "is-active" : ""}`}
                onClick={() => setSocialPlatform("instagram")}
                style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}
              >
                <Camera size={13} strokeWidth={1.5} />
                <span>Instagram Reels</span>
              </button>

              <button
                type="button"
                className={`seg-pill-btn ${socialPlatform === "youtube" ? "is-active" : ""}`}
                onClick={() => setSocialPlatform("youtube")}
                style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}
              >
                <Video size={13} strokeWidth={1.5} />
                <span>YouTube Shorts</span>
              </button>
            </div>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "10px",
                background: "var(--splic-bg-surface)",
                border: "1px solid var(--splic-border-subtle)",
                borderRadius: "8px",
                padding: "10px 12px",
                marginBottom: "14px",
              }}
            >
              <span style={{ fontSize: "11px", color: "var(--splic-text-muted)" }}>
                {isSelectedPlatformConnected
                  ? `${platformLabel}: ${platformSocial.handle || "connected"}`
                  : `${platformLabel} account is not connected`}
              </span>
              <span className={`splic-link-status-badge ${isSelectedPlatformConnected ? "is-connected" : "is-disconnected"}`}>
                {isSelectedPlatformConnected ? <Check size={11} strokeWidth={2} /> : null}
                {isSelectedPlatformConnected ? "Connected" : "Disconnected"}
              </span>
            </div>

            <div className="splic-form-group">
              <label>Post Title</label>
              <input
                type="text"
                className="splic-form-input"
                value={videoTitle}
                onChange={(e) => setVideoTitle(e.target.value)}
                placeholder="Enter engaging title..."
              />
            </div>

            <div className="splic-form-group">
              <label>Caption & Hashtags</label>
              <textarea
                className="splic-form-input"
                rows={4}
                value={videoDescription}
                onChange={(e) => setVideoDescription(e.target.value)}
                placeholder="Write caption with hashtags..."
                style={{ resize: "none" }}
              />
            </div>

            <div className="splic-form-group">
              <label>Visibility</label>
              <select
                className="splic-form-input"
                value={privacy}
                onChange={(e) => setPrivacy(e.target.value)}
              >
                <option value="public">Public (Instant Publish)</option>
                <option value="unlisted">Unlisted (Review Draft)</option>
                <option value="private">Private</option>
              </select>
            </div>
          </div>

          <div className="deliver-panel-footer">
            {socialUploadState === "success" ? (
              <div
                style={{
                  background: "rgba(34, 197, 94, 0.12)",
                  border: "1px solid rgba(34, 197, 94, 0.3)",
                  borderRadius: "8px",
                  minHeight: "44px",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "4px",
                  color: "#4ade80",
                  fontSize: "12px",
                  fontWeight: 700,
                  width: "100%",
                  boxSizing: "border-box",
                  padding: "10px 12px",
                }}
              >
                <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <CheckCircle2 size={16} strokeWidth={2} />
                  <span>Published to {platformLabel}</span>
                </span>
                {publishedResult?.post_url ? (
                  <a
                    href={publishedResult.post_url}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      fontSize: "11px",
                      fontWeight: 500,
                      color: "#4ade80",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "4px",
                    }}
                  >
                    <ExternalLink size={11} strokeWidth={1.75} />
                    <span>View published post</span>
                  </a>
                ) : publishedResult?.post_id ? (
                  <span style={{ fontSize: "11px", fontWeight: 500 }}>
                    Post id {publishedResult.post_id}
                  </span>
                ) : null}
              </div>
            ) : !isSelectedPlatformConnected ? (
              <button
                type="button"
                className="deliver-primary-btn"
                onClick={() => (onOpenSettings ? onOpenSettings() : null)}
              >
                <Share2 size={15} strokeWidth={1.5} />
                <span>Connect {platformLabel} Account in Settings</span>
              </button>
            ) : (
              <div style={{ width: "100%" }}>
                {publishError ? (
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
                      marginBottom: "10px",
                      fontSize: "11px",
                      lineHeight: 1.45,
                      color: "#fda4af",
                    }}
                  >
                    <AlertCircle size={13} strokeWidth={1.5} style={{ flexShrink: 0, marginTop: "1px" }} />
                    <span>{publishError}</span>
                  </div>
                ) : null}

                <button
                  type="button"
                  className="deliver-primary-btn"
                  disabled={publishing || exporting}
                  onClick={handleSocialPublish}
                >
                  {publishing ? (
                    <>
                      <RefreshCw size={15} className="spin-icon" strokeWidth={1.5} />
                      <span>
                        {socialUploadState === "rendering"
                          ? "Rendering reel..."
                          : `Publishing to ${platformLabel}...`}
                      </span>
                    </>
                  ) : (
                    <>
                      <Share2 size={15} strokeWidth={1.5} />
                      <span>Publish Directly to {platformLabel}</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
