import React, { useState } from "react";
import { X, Sparkles, ArrowRight, Smartphone, Monitor, Square, Layers, Film } from "lucide-react";

export const ASPECT_RATIO_PRESETS = [
  {
    id: "9:16",
    platform: "instagram-reel",
    name: "Instagram Reel",
    ratio: "9:16",
    resolution: "1080 × 1920",
    desc: "Vertical short-form with UI safe zone",
    wireframeType: "reel",
    recommended: true,
  },
  {
    id: "9:16-shorts",
    platform: "youtube-shorts",
    name: "YouTube Shorts",
    ratio: "9:16",
    resolution: "1080 × 1920",
    desc: "High bitrate vertical shorts feed",
    wireframeType: "shorts",
    recommended: false,
  },
  {
    id: "16:9",
    platform: "youtube-video",
    name: "YouTube Video",
    ratio: "16:9",
    resolution: "1920 × 1080",
    desc: "Cinematic landscape widescreen",
    wireframeType: "video",
    recommended: false,
  },
  {
    id: "1:1",
    platform: "instagram-square",
    name: "Square Post",
    ratio: "1:1",
    resolution: "1080 × 1080",
    desc: "Feed carousel & LinkedIn post",
    wireframeType: "square",
    recommended: false,
  },
  {
    id: "4:5",
    platform: "instagram-portrait",
    name: "Portrait Feed",
    ratio: "4:5",
    resolution: "1080 × 1350",
    desc: "Optimal Instagram feed real-estate",
    wireframeType: "portrait",
    recommended: false,
  },
];

export function NewProjectModal({
  isOpen = true,
  onClose,
  onCreateProject,
}) {
  const [title, setTitle] = useState("Untitled Reel #01");
  const [selectedRatioId, setSelectedRatioId] = useState("9:16");
  const [fps, setFps] = useState(30);
  const [languageMode, setLanguageMode] = useState("hinglish");

  if (!isOpen) return null;

  const handleCreate = (e) => {
    e?.preventDefault();
    const preset = ASPECT_RATIO_PRESETS.find((p) => p.id === selectedRatioId) || ASPECT_RATIO_PRESETS[0];
    const normalizedRatio = selectedRatioId.startsWith("9:16") ? "9:16" : selectedRatioId;
    if (onCreateProject) {
      onCreateProject({
        id: `proj-${Date.now()}`,
        name: title.trim() || "Untitled Project",
        ratioId: normalizedRatio,
        platformPreset: preset.name,
        fps,
        languageMode,
        updatedAt: Date.now(),
      });
    }
    if (onClose) onClose();
  };

  return (
    <div className="splic-modal-overlay">
      <div className="splic-modal-card">
        {/* Header */}
        <div className="splic-modal-header">
          <div>
            <h2 className="splic-modal-title">Create New Project</h2>
            <p style={{ margin: "4px 0 0 0", fontSize: "13px", color: "var(--splic-text-muted)" }}>
              Choose your target platform perspective & canvas format
            </p>
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

        <form onSubmit={handleCreate}>
          {/* Project Title Input */}
          <div className="splic-form-group" style={{ marginBottom: "22px" }}>
            <label>Project Title</label>
            <input
              type="text"
              className="splic-form-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Zomato UPI Viral Breakdown"
              autoFocus
              required
            />
          </div>

          {/* Aspect Ratio Perspective Cards Grid */}
          <div style={{ marginBottom: "8px" }}>
            <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--splic-text-subtle)", display: "block", marginBottom: "8px" }}>
              Target Platform & Perspective
            </label>
          </div>

          <div className="splic-aspect-grid">
            {ASPECT_RATIO_PRESETS.map((preset) => {
              const isSelected = selectedRatioId === preset.id;
              return (
                <div
                  key={preset.id}
                  className={`splic-aspect-card ${isSelected ? "is-selected" : ""}`}
                  onClick={() => setSelectedRatioId(preset.id)}
                >
                  {/* Visual Perspective Wireframe */}
                  <div className="splic-aspect-wireframe-stage">
                    {preset.wireframeType === "reel" && (
                      <div className="splic-wireframe-reel">
                        <div style={{ position: "absolute", top: "4px", left: "4px", width: "12px", height: "2px", background: "currentColor", opacity: 0.4 }} />
                        <div style={{ position: "absolute", bottom: "4px", left: "4px", width: "18px", height: "3px", background: "currentColor", opacity: 0.6 }} />
                      </div>
                    )}
                    {preset.wireframeType === "shorts" && (
                      <div className="splic-wireframe-reel">
                        <div style={{ position: "absolute", top: "5px", right: "3px", width: "3px", height: "3px", borderRadius: "50%", background: "#ff0000" }} />
                        <div style={{ position: "absolute", bottom: "4px", left: "4px", width: "16px", height: "3px", background: "currentColor", opacity: 0.6 }} />
                      </div>
                    )}
                    {preset.wireframeType === "video" && (
                      <div className="splic-wireframe-video">
                        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
                          <Film size={14} strokeWidth={1.25} style={{ opacity: 0.5 }} />
                        </div>
                      </div>
                    )}
                    {preset.wireframeType === "square" && (
                      <div className="splic-wireframe-square">
                        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
                          <Square size={14} strokeWidth={1.25} style={{ opacity: 0.5 }} />
                        </div>
                      </div>
                    )}
                    {preset.wireframeType === "portrait" && (
                      <div className="splic-wireframe-reel" style={{ height: "46px" }}>
                        <div style={{ position: "absolute", bottom: "4px", left: "4px", width: "14px", height: "3px", background: "currentColor", opacity: 0.5 }} />
                      </div>
                    )}
                  </div>

                  <span className="splic-aspect-name">{preset.name}</span>
                  <span className="splic-aspect-ratio-tag">{preset.ratio} • {preset.resolution}</span>
                  <span className="splic-aspect-desc">{preset.desc}</span>
                </div>
              );
            })}
          </div>

          {/* Quick Settings Row: FPS & Transliteration Language */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "26px" }}>
            <div className="splic-form-group">
              <label>Frame Rate</label>
              <div className="deliver-segmented-pill">
                {[30, 60].map((rate) => (
                  <button
                    key={rate}
                    type="button"
                    className={`seg-pill-btn ${fps === rate ? "is-active" : ""}`}
                    onClick={() => setFps(rate)}
                  >
                    {rate} FPS
                  </button>
                ))}
              </div>
            </div>

            <div className="splic-form-group">
              <label>Sarvam AI Captions</label>
              <div className="deliver-segmented-pill">
                <button
                  type="button"
                  className={`seg-pill-btn ${languageMode === "hinglish" ? "is-active" : ""}`}
                  onClick={() => setLanguageMode("hinglish")}
                >
                  Romanized Hinglish
                </button>
                <button
                  type="button"
                  className={`seg-pill-btn ${languageMode === "dual" ? "is-active" : ""}`}
                  onClick={() => setLanguageMode("dual")}
                >
                  Dual Subtitles
                </button>
              </div>
            </div>
          </div>

          {/* Submit Action */}
          <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end" }}>
            <button
              type="button"
              className="splic-btn-secondary"
              style={{ width: "auto", padding: "11px 20px" }}
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="splic-btn-primary"
              style={{ width: "auto", padding: "11px 28px" }}
            >
              <Sparkles size={15} strokeWidth={1.75} />
              <span>Launch Studio</span>
              <ArrowRight size={15} strokeWidth={2} />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

