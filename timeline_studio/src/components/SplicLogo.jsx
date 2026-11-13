import React from "react";

export function SplicInlaidEmblem({
  size = 320,
  showText = true,
  className = "",
}) {
  return (
    <div
      className={`splic-inlaid-emblem-wrap ${className}`}
      style={{
        display: "inline-flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
        userSelect: "none",
      }}
    >
      <svg
        width={size}
        height={Math.round(size * 0.72)}
        viewBox="0 0 160 120"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="splic-inlaid-vector-mark"
        style={{
          filter: "none",
          overflow: "visible",
        }}
      >
        {/* Timeline ruler ticks at top */}
        <g className="splic-inlaid-ticks" stroke="#e53935" strokeWidth="2" strokeLinecap="round" opacity="0.75">
          <line x1="8" y1="12" x2="8" y2="20" strokeWidth="2.5" />
          <line x1="16" y1="15" x2="16" y2="20" />
          <line x1="24" y1="15" x2="24" y2="20" />
          <line x1="32" y1="15" x2="32" y2="20" />
          <line x1="40" y1="12" x2="40" y2="20" strokeWidth="2.5" />
          <line x1="48" y1="15" x2="48" y2="20" />
          <line x1="56" y1="15" x2="56" y2="20" />
          <line x1="64" y1="15" x2="64" y2="20" />
          <line x1="72" y1="12" x2="72" y2="20" strokeWidth="2.5" />
          <line x1="80" y1="15" x2="80" y2="20" />
          <line x1="88" y1="15" x2="88" y2="20" />
          <line x1="96" y1="15" x2="96" y2="20" />
          <line x1="104" y1="12" x2="104" y2="20" strokeWidth="2.5" />
          <line x1="112" y1="15" x2="112" y2="20" />
          <line x1="120" y1="15" x2="120" y2="20" />
          <line x1="128" y1="15" x2="128" y2="20" />
          <line x1="136" y1="12" x2="136" y2="20" strokeWidth="2.5" />
          <line x1="144" y1="15" x2="144" y2="20" />
          <line x1="152" y1="12" x2="152" y2="20" strokeWidth="2.5" />
        </g>

        {/* Track 1: Media Footage (Flat Red) */}
        <g className="splic-inlaid-track splic-inlaid-track-1">
          <polygon points="15,26 80,26 73,42 8,42" fill="#e53935" />
          <polygon points="85,26 118,26 111,42 78,42" fill="#e53935" />
          <polygon points="123,26 155,26 148,42 116,42" fill="#e53935" />
        </g>

        {/* Track 2: Sticker Overlay Layer (Flat Medium Red) */}
        <g className="splic-inlaid-track splic-inlaid-track-2">
          <polygon points="12,47 43,47 36,63 5,63" fill="#d32f2f" />
          <polygon points="48,47 105,47 98,63 41,63" fill="#d32f2f" />
          <polygon points="110,47 154,47 147,63 103,63" fill="#d32f2f" />
        </g>

        {/* Track 3: Special Effects Layer (Flat Darker Red) */}
        <g className="splic-inlaid-track splic-inlaid-track-3">
          <polygon points="28,68 64,68 57,84 21,84" fill="#c62828" />
          <polygon points="69,68 93,68 86,84 62,84" fill="#c62828" />
          <polygon points="98,68 156,68 149,84 91,84" fill="#c62828" />
        </g>

        {/* Track 4: Audio & SFX Layer (Flat Deep Red) */}
        <g className="splic-inlaid-track splic-inlaid-track-4">
          <polygon points="15,89 59,89 52,105 8,105" fill="#b71c1c" />
          <polygon points="64,89 127,89 120,105 57,105" fill="#b71c1c" />
          <polygon points="132,89 155,89 148,105 125,105" fill="#b71c1c" />
        </g>
      </svg>

      {showText && (
        <div className="splic-inlaid-brand-text" style={{ marginTop: "16px", textAlign: "center" }}>
          <span
            style={{
              fontSize: `${Math.max(16, Math.round(size * 0.08))}px`,
              fontWeight: 800,
              letterSpacing: "0.22em",
              color: "#f5f6f8",
              display: "block",
              lineHeight: 1,
            }}
          >
            SPLIC
          </span>
          <span
            style={{
              fontSize: `${Math.max(9, Math.round(size * 0.04))}px`,
              fontWeight: 600,
              letterSpacing: "0.28em",
              color: "#e53935",
              marginTop: "5px",
              display: "block",
              lineHeight: 1,
              textTransform: "uppercase",
            }}
          >
            STUDIO
          </span>
        </div>
      )}
    </div>
  );
}

export function SplicLogo({
  size = 32,
  showText = true,
  variant = "mark", // "mark" | "image" | "full"
  className = "",
}) {
  return (
    <div className={`splic-logo-container ${className}`} style={{ display: "inline-flex", alignItems: "center", gap: "10px" }}>
      {variant === "image" ? (
        <img
          src="/assets/branding/splic-logo.jpg"
          alt="Splic Studio Logo"
          style={{
            height: `${size}px`,
            width: "auto",
            borderRadius: "6px",
            objectFit: "contain",
          }}
        />
      ) : (
        <svg
          width={size}
          height={Math.round(size * 0.75)}
          viewBox="0 0 160 120"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="splic-vector-mark"
          style={{ flexShrink: 0 }}
        >
          <defs>
            <linearGradient id="splicTrackGrad1" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#e85a4a" />
              <stop offset="100%" stopColor="#d33828" />
            </linearGradient>
            <linearGradient id="splicTrackGrad2" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#df4738" />
              <stop offset="100%" stopColor="#c02b1e" />
            </linearGradient>
            <linearGradient id="splicTrackGrad3" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#cf3d30" />
              <stop offset="100%" stopColor="#ab241a" />
            </linearGradient>
            <linearGradient id="splicTrackGrad4" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#b82d22" />
              <stop offset="100%" stopColor="#871812" />
            </linearGradient>
          </defs>

          {/* Timeline ruler ticks at top */}
          <g stroke="#9e4b44" strokeWidth="2.5" strokeLinecap="round">
            <line x1="8" y1="12" x2="8" y2="20" strokeWidth="3" />
            <line x1="16" y1="15" x2="16" y2="20" />
            <line x1="24" y1="15" x2="24" y2="20" />
            <line x1="32" y1="15" x2="32" y2="20" />
            <line x1="40" y1="12" x2="40" y2="20" strokeWidth="3" />
            <line x1="48" y1="15" x2="48" y2="20" />
            <line x1="56" y1="15" x2="56" y2="20" />
            <line x1="64" y1="15" x2="64" y2="20" />
            <line x1="72" y1="12" x2="72" y2="20" strokeWidth="3" />
            <line x1="80" y1="15" x2="80" y2="20" />
            <line x1="88" y1="15" x2="88" y2="20" />
            <line x1="96" y1="15" x2="96" y2="20" />
            <line x1="104" y1="12" x2="104" y2="20" strokeWidth="3" />
            <line x1="112" y1="15" x2="112" y2="20" />
            <line x1="120" y1="15" x2="120" y2="20" />
            <line x1="128" y1="15" x2="128" y2="20" />
            <line x1="136" y1="12" x2="136" y2="20" strokeWidth="3" />
            <line x1="144" y1="15" x2="144" y2="20" />
            <line x1="152" y1="12" x2="152" y2="20" strokeWidth="3" />
          </g>

          {/* Track 1: Media Footage (Skewed Blocks) */}
          <polygon points="15,26 80,26 73,42 8,42" fill="url(#splicTrackGrad1)" />
          <polygon points="85,26 118,26 111,42 78,42" fill="url(#splicTrackGrad1)" />
          <polygon points="123,26 155,26 148,42 116,42" fill="url(#splicTrackGrad1)" />

          {/* Track 2: Sticker Overlay Layer (Skewed Blocks) */}
          <polygon points="12,47 43,47 36,63 5,63" fill="url(#splicTrackGrad2)" />
          <polygon points="48,47 105,47 98,63 41,63" fill="url(#splicTrackGrad2)" />
          <polygon points="110,47 154,47 147,63 103,63" fill="url(#splicTrackGrad2)" />

          {/* Track 3: Special Effects Layer (Skewed Blocks) */}
          <polygon points="28,68 64,68 57,84 21,84" fill="url(#splicTrackGrad3)" />
          <polygon points="69,68 93,68 86,84 62,84" fill="url(#splicTrackGrad3)" />
          <polygon points="98,68 156,68 149,84 91,84" fill="url(#splicTrackGrad3)" />

          {/* Track 4: Audio & SFX Layer (Skewed Blocks) */}
          <polygon points="15,89 59,89 52,105 8,105" fill="url(#splicTrackGrad4)" />
          <polygon points="64,89 127,89 120,105 57,105" fill="url(#splicTrackGrad4)" />
          <polygon points="132,89 155,89 148,105 125,105" fill="url(#splicTrackGrad4)" />
        </svg>
      )}

      {showText && (
        <div className="splic-brand-text" style={{ display: "flex", flexDirection: "column", lineHeight: 1 }}>
          <span
            style={{
              fontSize: `${Math.max(14, Math.round(size * 0.44))}px`,
              fontWeight: 800,
              letterSpacing: "0.08em",
              color: "#f5f6f8",
              fontFamily: "Inter, system-ui, sans-serif",
            }}
          >
            SPLIC
          </span>
          <span
            style={{
              fontSize: `${Math.max(8, Math.round(size * 0.22))}px`,
              fontWeight: 600,
              letterSpacing: "0.14em",
              color: "#e53935",
              marginTop: "2px",
              textTransform: "uppercase",
            }}
          >
            STUDIO
          </span>
        </div>
      )}
    </div>
  );
}

