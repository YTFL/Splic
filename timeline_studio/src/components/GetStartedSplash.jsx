import React from "react";
import { Settings, User, ArrowRight } from "lucide-react";

export function GetStartedSplash({ onGetStarted, onSignIn }) {
  const handleProceed = onSignIn || onGetStarted;

  return (
    <div className="splic-minimal-home">
      {/* Sleek VS Code Style Top Window Bar */}
      <header className="splic-minimal-topbar">
        {/* Left: macOS Traffic Light Dots */}
        <div className="splic-window-dots">
          <span className="splic-dot is-red" />
          <span className="splic-dot is-yellow" />
          <span className="splic-dot is-green" />
        </div>

        {/* Center: Window Title + Sign In Pill Button (Exact to screenshot) */}
        <div className="splic-minimal-topbar-center">
          <span className="splic-minimal-app-title">Splic Studio</span>
          <button
            type="button"
            className="splic-topbar-signin-pill"
            onClick={handleProceed}
          >
            Sign In
          </button>
        </div>

        {/* Right: Minimal Utility Icons */}
        <div className="splic-minimal-topbar-right">
          <button
            type="button"
            className="splic-minimal-icon-btn"
            onClick={handleProceed}
            title="Account"
          >
            <User size={15} strokeWidth={1.5} />
          </button>
          <button
            type="button"
            className="splic-minimal-icon-btn"
            onClick={handleProceed}
            title="Settings"
          >
            <Settings size={15} strokeWidth={1.5} />
          </button>
        </div>
      </header>

      {/* Main Center Stage: Minimal, spacious, featuring the provided logo */}
      <main
        className="splic-minimal-stage"
        onClick={handleProceed}
        role="button"
        tabIndex={0}
      >
        <div className="splic-minimal-watermark-wrap">
          <img
            src="/assets/branding/splic-logo.jpg"
            alt="Splic Studio"
            className="splic-minimal-watermark-logo"
          />
        </div>

        <div className="splic-minimal-cta-wrap">
          <button
            type="button"
            className="splic-minimal-getstarted-btn"
            onClick={(e) => {
              e.stopPropagation();
              handleProceed();
            }}
          >
            <span>Get Started</span>
            <ArrowRight size={14} strokeWidth={2} />
          </button>
          <span className="splic-minimal-hint">
            Click anywhere or Sign In to open your workspace
          </span>
        </div>
      </main>
    </div>
  );
}
