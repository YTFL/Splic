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
} from "lucide-react";

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
      id: "editor",
      label: "Editor",
      sublabel: "Cut & Assembly",
      icon: Film,
    },
    {
      id: "smart",
      label: "Smart / AI",
      sublabel: "Auto-Cut & Subtitles",
      icon: Sparkles,
      badge: "Sarvam",
    },
    {
      id: "export",
      label: "Deliver & Share",
      sublabel: "Export & Social",
      icon: Rocket,
    },
  ];

  return (
    <footer className="davinci-bottom-bar" role="navigation" aria-label="Workspace Pages">
      {/* Left status & project format */}
      <div className="davinci-bottom-left">
        <div className="davinci-logo-badge">
          <span className="davinci-dot" />
          <span className="davinci-app-name">SPLIC STUDIO</span>
        </div>
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
            aria-label={isPlaying ? "Pause" : "Play"}
          >
            {isPlaying ? (
              <Pause size={13} strokeWidth={1.25} />
            ) : (
              <Play size={13} strokeWidth={1.25} />
            )}
          </button>
        ) : null}

        <div className="davinci-timecode-box" title="Playhead Timecode (HH:MM:SS:FF)">
          <Clock size={12} strokeWidth={1.25} />
          <span className="davinci-tc-val">{formatTimecode(currentTime)}</span>
          <span className="davinci-tc-sep">/</span>
          <span className="davinci-tc-total">{formatTimecode(duration)}</span>
        </div>

        <div className="davinci-audio-meter-peek" title="Stereo Audio Monitor">
          <Volume2 size={12} strokeWidth={1.25} />
          <div className="davinci-vu-bars">
            <span className={`vu-bar ${isPlaying ? "vu-active-1" : ""}`} />
            <span className={`vu-bar ${isPlaying ? "vu-active-2" : ""}`} />
            <span className={`vu-bar ${isPlaying ? "vu-active-3" : ""}`} />
          </div>
        </div>
      </div>
    </footer>
  );
}
