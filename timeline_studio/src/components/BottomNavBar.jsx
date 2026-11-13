import React from "react";
import {
  Film,
  Sparkles,
  Rocket,
  Play,
  Pause,
  Volume2,
  Clock,
  Layers,
  FolderKanban,
} from "lucide-react";
import { SplicLogo } from "./SplicLogo.jsx";

export function BottomNavBar({
  activePage = "editor",
  onSelectPage,
  currentTime = 0,
  duration = 0,
  ratioId = "9:16",
  isPlaying = false,
  onTogglePlay,
  t = (k, fallback) => fallback || k,
}) {
  const formatTimecode = (seconds) => {
    if (isNaN(seconds) || seconds < 0) seconds = 0;
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const frames = Math.floor((seconds % 1) * 30);
    const pad = (n) => String(n).padStart(2, "0");
    return `${pad(hrs)}:${pad(mins)}:${pad(secs)}:${pad(frames)}`;
  };

  const pages = [
    {
      id: "projects",
      label: "Projects",
      sublabel: "Dashboard",
      icon: FolderKanban,
    },
    {
      id: "editor",
      label: "Editor",
      sublabel: "Timeline & Preview",
      icon: Film,
    },
    {
      id: "smart",
      label: "Auto Edit",
      sublabel: "Auto-Cut",
      icon: Sparkles,
    },
    {
      id: "export",
      label: "Export",
      sublabel: "Deliver Video",
      icon: Rocket,
    },
  ];

  return (
    <footer className="davinci-bottom-bar" role="navigation" aria-label="Workspace Pages">
      {/* Left status & Splic logo */}
      <div className="davinci-bottom-left" style={{ display: "flex", alignItems: "center", gap: "14px" }}>
        <button
          type="button"
          onClick={() => onSelectPage?.("projects")}
          style={{ background: "none", border: "none", padding: 0, cursor: "pointer", display: "flex", alignItems: "center" }}
          title="Return to Projects Dashboard"
        >
          <SplicLogo size={20} showText={true} />
        </button>

        <div className="davinci-format-tag">
          <Layers size={13} strokeWidth={1.25} />
          <span>{ratioId}</span>
          <span className="davinci-divider">•</span>
          <span>30 FPS</span>
        </div>
      </div>

      {/* Center workspace page switcher */}
      <div className="davinci-page-switcher" role="tablist">
        {pages.map(({ id, label, icon: Icon, badge }) => {
          const isActive = activePage === id;
          return (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={isActive}
              className={`davinci-page-tab ${isActive ? "is-active" : ""}`}
              onClick={() => onSelectPage?.(id)}
            >
              <div className="davinci-tab-icon-wrap">
                <Icon size={16} strokeWidth={isActive ? 1.75 : 1.25} />
                {badge ? <span className="davinci-tab-badge">{badge}</span> : null}
              </div>
              <span className="davinci-tab-title">{label}</span>
              {isActive && <span className="davinci-tab-indicator" />}
            </button>
          );
        })}
      </div>

      {/* Right transport & audio monitor readout */}
      <div className="davinci-bottom-right">
        {onTogglePlay ? (
          <button
            type="button"
            className="davinci-mini-transport"
            onClick={onTogglePlay}
            aria-label={isPlaying ? "Pause timeline" : "Play timeline"}
            title="Spacebar to toggle playback"
          >
            {isPlaying ? (
              <Pause size={13} strokeWidth={1.75} />
            ) : (
              <Play size={13} strokeWidth={1.75} style={{ marginLeft: "1px" }} />
            )}
          </button>
        ) : null}

        <div className="davinci-timecode-display" title="Playhead Position / Composition Duration">
          <Clock size={12} strokeWidth={1.25} className="davinci-timecode-icon" />
          <span className="timecode-current">{formatTimecode(currentTime)}</span>
          <span className="timecode-sep">/</span>
          <span className="timecode-total">{formatTimecode(duration)}</span>
        </div>

        <div className="davinci-audio-meter-compact" title="Master Audio Bus (dBFS)">
          <Volume2 size={12} strokeWidth={1.25} />
          <div className="audio-meter-bar">
            <span className="meter-channel left" style={{ height: isPlaying ? "65%" : "4%" }} />
            <span className="meter-channel right" style={{ height: isPlaying ? "72%" : "4%" }} />
          </div>
        </div>
      </div>
    </footer>
  );
}
