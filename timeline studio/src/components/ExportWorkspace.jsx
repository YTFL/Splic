import React, { useState } from "react";
import {
  Download,
  Share2,
  Clapperboard,
  Camera,
  Sliders,
  CheckCircle2,
  Clock,
  Film,
  Sparkles,
  Layers,
  HardDrive,
  Eye,
  RefreshCw,
  Video,
  FileVideo,
  Check,
} from "lucide-react";

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
  t = (k, fallback) => fallback || k,
}) {
  const [selectedPreset, setSelectedPreset] = useState("instagram-reels");
  const [socialPlatform, setSocialPlatform] = useState("instagram");
  const [videoTitle, setVideoTitle] = useState("My Desi Reel — Splic Studio");
  const [videoDescription, setVideoDescription] = useState(
    "Created with Splic Studio #DesiAutoCut #SarvamAI #Reels"
  );
  const [tags, setTags] = useState("desi, reel, comedy, viral, sarvam");
  const [privacy, setPrivacy] = useState("public");
  const [qualityPreset, setQualityPreset] = useState("high");
  const [burnCaptions, setBurnCaptions] = useState(true);
  const [socialUploadState, setSocialUploadState] = useState("idle"); // "idle" | "uploading" | "success"

  const presets = [
    {
      id: "instagram-reels",
      name: "Instagram Reels",
      format: "9:16 Vertical",
      resolution: "1080 x 1920",
      fps: "30 / 60 FPS",
      bitrate: "12 Mbps (H.264)",
      badge: "Reels / Stories",
      recommended: true,
    },
    {
      id: "youtube-shorts",
      name: "YouTube Shorts",
      format: "9:16 Vertical",
      resolution: "1080 x 1920",
      fps: "60 FPS",
      bitrate: "15 Mbps (H.264)",
      badge: "Shorts",
    },
    {
      id: "youtube-hd",
      name: "YouTube 16:9 HD",
      format: "16:9 Landscape",
      resolution: "1920 x 1080",
      fps: "30 / 60 FPS",
      bitrate: "16 Mbps (H.264)",
      badge: "Full HD",
    },
    {
      id: "custom-pro",
      name: "Custom Master",
      format: "NLE Master",
      resolution: "Native Source",
      fps: "Project FPS",
      bitrate: "Maximum Quality",
      badge: "Lossless",
    },
  ];

  const handleStartExport = () => {
    if (onExportVideo) {
      onExportVideo({
        preset: selectedPreset,
        quality: qualityPreset,
        burnCaptions,
      });
    }
  };

  const handleSocialPublish = () => {
    setSocialUploadState("uploading");
    setTimeout(() => {
      setSocialUploadState("success");
    }, 2200);
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
          <Film size={18} strokeWidth={1.25} />
          <h2 className="deliver-header-title">Deliver & Social Publish</h2>
          <span className="deliver-header-badge">WebCodecs Hardware Accelerated</span>
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
        </div>
      </header>

      {/* Main Deliver Grid */}
      <div className="davinci-deliver-grid">
        {/* Left: Render Settings & Format Presets */}
        <section className="deliver-panel deliver-presets-panel">
          <div className="deliver-panel-title">
            <FileVideo size={15} strokeWidth={1.25} />
            <span>Export Format Presets</span>
          </div>

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
                      <Check size={13} strokeWidth={1.5} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="deliver-encoding-options">
            <div className="deliver-panel-title">
              <Sliders size={15} strokeWidth={1.25} />
              <span>Encoding Parameters</span>
            </div>

            <div className="deliver-option-row">
              <label>Quality Target</label>
              <div className="deliver-segmented-pill">
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

            <div className="deliver-option-row">
              <label>Burn Indic Karaoke Subtitles</label>
              <input
                type="checkbox"
                checked={burnCaptions}
                onChange={(e) => setBurnCaptions(e.target.checked)}
                className="deliver-checkbox"
              />
            </div>
          </div>

          <div className="deliver-render-cta">
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
                  <span>Export MP4 Video</span>
                </>
              )}
            </button>
          </div>
        </section>

        {/* Center: Live Composition Preview */}
        <section className="deliver-panel deliver-preview-panel">
          <div className="deliver-panel-title">
            <Eye size={15} strokeWidth={1.25} />
            <span>Master Output Preview</span>
          </div>

          <div className="deliver-preview-stage">
            <div className="deliver-video-container">
              {/* Reference preview display */}
              <div className="deliver-preview-placeholder">
                <Video size={36} strokeWidth={1.25} />
                <span className="deliver-preview-caption">
                  Active Timeline Media ({ratioId})
                </span>
                <span className="deliver-preview-sub">
                  Full 1080p hardware-accelerated preview
                </span>
              </div>
            </div>

            {exporting && (
              <div className="deliver-live-progress-box">
                <div className="progress-top-info">
                  <span className="progress-label">{exportPhase || "Rendering Video Frames..."}</span>
                  <span className="progress-num">{exportPercent}%</span>
                </div>
                <div className="progress-bar-track">
                  <div
                    className="progress-bar-fill"
                    style={{ width: `${exportPercent}%` }}
                  />
                </div>
                {onCancelExport && (
                  <button
                    type="button"
                    className="deliver-cancel-btn"
                    onClick={onCancelExport}
                  >
                    Cancel Render
                  </button>
                )}
              </div>
            )}
          </div>
        </section>

        {/* Right: Direct Social Media Upload */}
        <section className="deliver-panel deliver-social-panel">
          <div className="deliver-panel-title">
            <Share2 size={15} strokeWidth={1.25} />
            <span>1-Click Social Media Upload</span>
          </div>

          <div className="social-tabs">
            <button
              type="button"
              className={`social-tab ${socialPlatform === "instagram" ? "is-active" : ""}`}
              onClick={() => setSocialPlatform("instagram")}
            >
              <Camera size={15} strokeWidth={1.25} />
              <span>Instagram Reels</span>
            </button>
            <button
              type="button"
              className={`social-tab ${socialPlatform === "youtube" ? "is-active" : ""}`}
              onClick={() => setSocialPlatform("youtube")}
            >
              <Clapperboard size={15} strokeWidth={1.25} />
              <span>YouTube Shorts</span>
            </button>
          </div>

          <div className="social-form">
            <div className="social-field">
              <label>Reel / Short Title</label>
              <input
                type="text"
                value={videoTitle}
                onChange={(e) => setVideoTitle(e.target.value)}
                placeholder="Enter compelling video title..."
              />
            </div>

            <div className="social-field">
              <label>Caption & Description</label>
              <textarea
                rows={4}
                value={videoDescription}
                onChange={(e) => setVideoDescription(e.target.value)}
                placeholder="Write caption with hashtags and credits..."
              />
            </div>

            <div className="social-field">
              <label>Tags & Hashtags</label>
              <input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="comma, separated, tags"
              />
            </div>

            <div className="social-field">
              <label>Visibility</label>
              <select
                value={privacy}
                onChange={(e) => setPrivacy(e.target.value)}
              >
                <option value="public">Public (Immediate Publish)</option>
                <option value="unlisted">Unlisted (Share via link)</option>
                <option value="private">Private (Draft)</option>
              </select>
            </div>

            <div className="social-upload-cta">
              {socialUploadState === "success" ? (
                <div className="social-success-banner">
                  <CheckCircle2 size={16} strokeWidth={1.5} />
                  <span>Ready to upload to {socialPlatform === "instagram" ? "Instagram" : "YouTube"}!</span>
                </div>
              ) : (
                <button
                  type="button"
                  className="social-publish-btn"
                  disabled={socialUploadState === "uploading"}
                  onClick={handleSocialPublish}
                >
                  {socialUploadState === "uploading" ? (
                    <>
                      <RefreshCw size={14} className="spin-icon" strokeWidth={1.5} />
                      <span>Preparing Upload Package...</span>
                    </>
                  ) : (
                    <>
                      <Share2 size={14} strokeWidth={1.5} />
                      <span>Publish Directly to {socialPlatform === "instagram" ? "Instagram" : "YouTube"}</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
