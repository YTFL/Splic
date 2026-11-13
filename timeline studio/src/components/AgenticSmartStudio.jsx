import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Zap,
  RotateCcw,
  Sparkles,
  Subtitles,
  Smile,
  Music,
  Video,
  Layers,
  Cpu,
  Clock,
  HardDrive,
  Check,
} from "lucide-react";

export function AgenticSmartStudio({
  onApplyToProject,
  t = (k, fallback) => fallback || k,
}) {
  const canvasRef = useRef(null);
  const animationFrameRef = useRef(null);
  const particlesRef = useRef([]);

  // Automated workflow sequence states
  const [workflowState, setWorkflowState] = useState("idle"); // "idle" | "running" | "completed"
  const [activeStep, setActiveStep] = useState(0); // 0: idle, 1: silence cut, 2: captions, 3: stickers, 4: sfx
  const [currentTaskLabel, setCurrentTaskLabel] = useState("Standing by — Click Run to start agentic edit");

  // Element states in the Ingestion Tray
  // state: "ready" | "dematerializing" | "teleported"
  const [rawElements, setRawElements] = useState([
    {
      id: "raw-video",
      type: "video",
      title: "Raw Indic Video",
      sub: "9:16 • 15.0s (3.15s dead air)",
      state: "ready",
    },
    {
      id: "caption-token-1",
      type: "caption",
      title: "Aaj hum baat karenge",
      sub: "Saaras v4 • 0.2s - 2.8s",
      state: "ready",
    },
    {
      id: "sticker-token-1",
      type: "sticker",
      title: "Zomato Brand Sticker",
      sub: "rembg Cutout • 1.25s",
      state: "ready",
    },
    {
      id: "caption-token-2",
      type: "caption",
      title: "Secret UPI Cashback Trick",
      sub: "Saaras v4 • 3.2s - 6.5s",
      state: "ready",
    },
    {
      id: "sfx-token-1",
      type: "sfx",
      title: "Vine Boom Meme SFX",
      sub: "Audio Cue • 6.65s",
      state: "ready",
    },
  ]);

  // Timeline track materialization states
  const [isSpliced, setIsSpliced] = useState(false);
  const [isDeadAirDeleted, setIsDeadAirDeleted] = useState(false);
  const [isRippled, setIsRippled] = useState(false);

  const [materializedCaptions, setMaterializedCaptions] = useState([]);
  const [materializedStickers, setMaterializedStickers] = useState([]);
  const [materializedSfx, setMaterializedSfx] = useState([]);

  // Particle emission helper
  const emitParticles = useCallback((sourceEl, targetEl, color = "#e05638", count = 55) => {
    const canvas = canvasRef.current;
    if (!canvas || !sourceEl || !targetEl) return;

    const canvasRect = canvas.getBoundingClientRect();
    const sRect = sourceEl.getBoundingClientRect();
    const tRect = targetEl.getBoundingClientRect();

    const startX = sRect.left + sRect.width / 2 - canvasRect.left;
    const startY = sRect.top + sRect.height / 2 - canvasRect.top;
    const targetX = tRect.left + tRect.width / 2 - canvasRect.left;
    const targetY = tRect.top + tRect.height / 2 - canvasRect.top;

    const colors = [color, "#ff9179", "#f59e0b", "#ffffff"];

    for (let i = 0; i < count; i++) {
      const pColor = colors[Math.floor(Math.random() * colors.length)];
      particlesRef.current.push({
        x: startX + (Math.random() - 0.5) * 30,
        y: startY + (Math.random() - 0.5) * 20,
        startX,
        startY,
        targetX: targetX + (Math.random() - 0.5) * 40,
        targetY: targetY + (Math.random() - 0.5) * 16,
        color: pColor,
        progress: 0,
        speed: 0.02 + Math.random() * 0.016,
        size: 2 + Math.random() * 3.5,
        alpha: 1,
        cpX: (startX + targetX) / 2 + (Math.random() - 0.5) * 140,
        cpY: Math.min(startY, targetY) - 50 - Math.random() * 90,
      });
    }
  }, []);

  // Main 60fps Canvas Render Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    const updateCanvasSize = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };
    updateCanvasSize();
    window.addEventListener("resize", updateCanvasSize);

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const particles = particlesRef.current;
      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        p.progress += p.speed;

        if (p.progress >= 1) {
          particles.splice(i, 1);
          continue;
        }

        const t = p.progress;
        p.x = (1 - t) * (1 - t) * p.startX + 2 * (1 - t) * t * p.cpX + t * t * p.targetX;
        p.y = (1 - t) * (1 - t) * p.startY + 2 * (1 - t) * t * p.cpY + t * t * p.targetY;

        if (p.progress > 0.8) {
          p.alpha = Math.max(0, (1 - p.progress) / 0.2);
        }

        ctx.save();
        ctx.globalAlpha = p.alpha;
        ctx.fillStyle = p.color;
        ctx.shadowColor = p.color;
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }

      animationFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener("resize", updateCanvasSize);
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    };
  }, []);

  // Run the full autonomous edit sequence
  const runAutonomousSequence = async () => {
    if (workflowState === "running") return;
    setWorkflowState("running");
    resetSequence(false);

    // STEP 1: Silence Detection & Splicing
    setActiveStep(1);
    setCurrentTaskLabel("Local Silence Detector: Scanning waveform for dead-air intervals (>0.8s)...");
    await delay(1200);

    setCurrentTaskLabel("Silence Detected: Splicing dead-air hesitation [3.15s - 5.40s]...");
    setIsSpliced(true);
    await delay(1000);

    // Explode dead air slice into particles
    const deadAirEl = document.getElementById("dead-air-splice-block");
    const videoTrackEl = document.getElementById("timeline-track-v1");
    if (deadAirEl && videoTrackEl) {
      emitParticles(deadAirEl, videoTrackEl, "#ff5533", 45);
    }
    setIsDeadAirDeleted(true);
    await delay(400);

    // Magnetic ripple snap
    setCurrentTaskLabel("Ripple Cut: Magnetic snapping video clips to eliminate dead air...");
    setIsRippled(true);
    await delay(1100);

    // STEP 2: Romanized Hinglish Subtitles Teleportation
    setActiveStep(2);
    setCurrentTaskLabel("Saaras v4 STT: Transliterating speech into Romanized Hinglish phonetic tokens...");
    await delay(900);

    // Dematerialize Caption 1
    triggerElementTeleport("caption-token-1", "timeline-track-c1", "#ffd600", () => {
      setMaterializedCaptions((prev) => [
        ...prev,
        { id: "c1", text: "Aaj hum baat karenge...", range: "0.2s - 2.8s" },
      ]);
    });
    await delay(1200);

    // Dematerialize Caption 2
    triggerElementTeleport("caption-token-2", "timeline-track-c1", "#ffd600", () => {
      setMaterializedCaptions((prev) => [
        ...prev,
        { id: "c2", text: "Secret UPI Cashback Trick ⚡", range: "3.2s - 6.5s" },
      ]);
    });
    await delay(1400);

    // STEP 3: Dynamic Indian Sticker Teleportation
    setActiveStep(3);
    setCurrentTaskLabel("Sarvam-105B Director: Detected entity 'Zomato' — Scraping & removing background via rembg...");
    await delay(1100);

    triggerElementTeleport("sticker-token-1", "timeline-track-s1", "#e05638", () => {
      setMaterializedStickers((prev) => [
        ...prev,
        { id: "s1", label: "Zomato Transparent PNG (PiP x:0.5, y:0.3)", duration: "2.5s" },
      ]);
    });
    await delay(1400);

    // STEP 4: Meme SFX & Punch-in Zooms
    setActiveStep(4);
    setCurrentTaskLabel("Meme Sound Director: Synchronizing 'vine_boom.mp3' & 1.25x punch-in zoom...");
    await delay(1000);

    triggerElementTeleport("sfx-token-1", "timeline-track-a1", "#22c55e", () => {
      setMaterializedSfx((prev) => [
        ...prev,
        { id: "a1", label: "vine_boom.mp3 (Vol: 0.8)", start: "6.65s" },
      ]);
    });
    await delay(1200);

    // COMPLETE!
    setWorkflowState("completed");
    setCurrentTaskLabel("Autonomous Agentic Edit Complete — All tracks synchronized & ready!");
  };

  const triggerElementTeleport = (elementId, targetTrackId, color, onLanded) => {
    // 1. Mark element as dematerializing
    setRawElements((items) =>
      items.map((item) => (item.id === elementId ? { ...item, state: "dematerializing" } : item))
    );

    const sourceEl = document.getElementById(elementId);
    const targetEl = document.getElementById(targetTrackId);

    // 2. Spawn particles
    if (sourceEl && targetEl) {
      emitParticles(sourceEl, targetEl, color, 60);
    }

    // 3. Mark element as teleported
    setTimeout(() => {
      setRawElements((items) =>
        items.map((item) => (item.id === elementId ? { ...item, state: "teleported" } : item))
      );
      onLanded();
    }, 600);
  };

  const resetSequence = (resetStatus = true) => {
    if (resetStatus) setWorkflowState("idle");
    setActiveStep(0);
    setIsSpliced(false);
    setIsDeadAirDeleted(false);
    setIsRippled(false);
    setMaterializedCaptions([]);
    setMaterializedStickers([]);
    setMaterializedSfx([]);
    setRawElements((items) => items.map((item) => ({ ...item, state: "ready" })));
    particlesRef.current = [];
    if (resetStatus) {
      setCurrentTaskLabel("Standing by — Click Run to start agentic edit");
    }
  };

  const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  const handleApplyToProject = () => {
    if (onApplyToProject) {
      onApplyToProject({
        captions: materializedCaptions,
        stickers: materializedStickers,
        sfx: materializedSfx,
        isSpliced,
      });
    }
  };

  return (
    <div className="agentic-studio-container">
      {/* 2D Particle Animation Canvas Overlay */}
      <canvas ref={canvasRef} className="agentic-particle-canvas" />

      {/* Top Header / Control Bar */}
      <header className="agentic-topbar">
        <div className="agentic-brand-group">
          <div className="agentic-pulse-dot" />
          <div className="agentic-title-group">
            <h2>Sarvam Indic Agentic Director</h2>
            <span>Autonomous Multi-Track Splicing & Synthesis</span>
          </div>
        </div>

        <div className="agentic-agent-pill">
          <Cpu size={14} strokeWidth={1.5} />
          <span>{currentTaskLabel}</span>
        </div>

        <div className="agentic-actions">
          {workflowState === "completed" ? (
            <button
              type="button"
              className="agentic-btn-primary"
              onClick={handleApplyToProject}
            >
              <Check size={14} strokeWidth={1.5} />
              <span>Apply Edits to Project Timeline</span>
            </button>
          ) : (
            <button
              type="button"
              className="agentic-btn-primary"
              disabled={workflowState === "running"}
              onClick={runAutonomousSequence}
            >
              <Zap size={14} strokeWidth={1.5} />
              <span>{workflowState === "running" ? "Running Agentic Flow..." : "Run Autonomous Auto-Cut"}</span>
            </button>
          )}

          <button
            type="button"
            className="agentic-btn-secondary"
            disabled={workflowState === "running"}
            onClick={() => resetSequence(true)}
            title="Reset Agent Sequence"
          >
            <RotateCcw size={13} strokeWidth={1.25} />
            <span>Reset</span>
          </button>
        </div>
      </header>

      {/* Main Two-Column Stage */}
      <div className="agentic-main-stage">
        {/* Left: Ingestion Tray & Placeholder Multi-Track Timeline */}
        <div className="agentic-canvas-stage">
          {/* Top: Ingestion Tray (Raw Videos & Elements Waiting to be Processed) */}
          <section className="agentic-ingestion-tray">
            <div className="ingestion-tray-header">
              <div className="tray-title">
                <HardDrive size={14} strokeWidth={1.25} />
                <span>Raw Asset Ingestion Tray (Awaiting Agent Teleportation)</span>
              </div>
              <span className="tray-count-tag">
                {rawElements.filter((e) => e.state === "ready").length} Pending
              </span>
            </div>

            <div className="ingestion-elements-row">
              {rawElements.map((el) => {
                const isDematerializing = el.state === "dematerializing";
                const isTeleported = el.state === "teleported";

                return (
                  <div
                    key={el.id}
                    id={el.id}
                    className={`raw-element-card is-${el.type} ${
                      isDematerializing ? "is-dematerializing" : ""
                    } ${isTeleported ? "is-teleported" : ""}`}
                  >
                    <div className="element-type-badge">
                      {el.type === "video" ? (
                        <Video size={12} strokeWidth={1.5} />
                      ) : el.type === "caption" ? (
                        <Subtitles size={12} strokeWidth={1.5} />
                      ) : el.type === "sticker" ? (
                        <Smile size={12} strokeWidth={1.5} />
                      ) : (
                        <Music size={12} strokeWidth={1.5} />
                      )}
                    </div>
                    <div className="element-meta-col">
                      <span className="element-meta-title">{el.title}</span>
                      <span className="element-meta-sub">{el.sub}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Bottom: Animated Placeholder Timeline */}
          <section className="agentic-timeline-board">
            <div className="agentic-timeline-header">
              <div className="timeline-board-title">
                <Layers size={15} strokeWidth={1.25} />
                <span>Agentic Placeholder Timeline (Live Automated Construction)</span>
              </div>
              <span className="tray-count-tag">
                {isRippled ? "Clean Cut • 12.75s Post-Ripple" : "15.0s Raw Clip"}
              </span>
            </div>

            <div className="timeline-tracks-stack">
              {/* V1: Spliced Video Track */}
              <div className="agentic-track-row">
                <span className="agentic-track-label">
                  <Video size={12} strokeWidth={1.25} />
                  <span>V1 Video</span>
                </span>
                <div id="timeline-track-v1" className="agentic-track-lane">
                  <div className="spliced-video-clip clip-segment-a">
                    <span>Clip A [0.0s - 3.15s]</span>
                  </div>

                  {/* Splicing Laser & Dead Air Segment */}
                  {isSpliced && !isDeadAirDeleted && (
                    <div id="dead-air-splice-block" className="dead-air-splice-target">
                      <div className="laser-cutter-line" />
                      <div className="spark-burst" />
                      <span>Dead Air [3.15s - 5.40s]</span>
                    </div>
                  )}

                  <div
                    className={`spliced-video-clip clip-segment-b ${
                      isRippled ? "is-rippled" : ""
                    }`}
                  >
                    <span>Clip B [5.40s - 15.0s]</span>
                  </div>
                </div>
              </div>

              {/* C1: Romanized Captions Track */}
              <div className="agentic-track-row">
                <span className="agentic-track-label">
                  <Subtitles size={12} strokeWidth={1.25} />
                  <span>C1 Text</span>
                </span>
                <div id="timeline-track-c1" className="agentic-track-lane">
                  {materializedCaptions.map((cap) => (
                    <div key={cap.id} className="materialized-clip is-caption-track">
                      <Subtitles size={11} strokeWidth={1.5} />
                      <span>{cap.text}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* S1: Dynamic Stickers Track */}
              <div className="agentic-track-row">
                <span className="agentic-track-label">
                  <Smile size={12} strokeWidth={1.25} />
                  <span>S1 PiP</span>
                </span>
                <div id="timeline-track-s1" className="agentic-track-lane">
                  {materializedStickers.map((stk) => (
                    <div key={stk.id} className="materialized-clip is-sticker-track">
                      <Smile size={11} strokeWidth={1.5} />
                      <span>{stk.label}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* A1: Audio & Meme SFX Track */}
              <div className="agentic-track-row">
                <span className="agentic-track-label">
                  <Music size={12} strokeWidth={1.25} />
                  <span>A1 Audio</span>
                </span>
                <div id="timeline-track-a1" className="agentic-track-lane">
                  {materializedSfx.map((sfx) => (
                    <div key={sfx.id} className="materialized-clip is-audio-track">
                      <Music size={11} strokeWidth={1.5} />
                      <span>{sfx.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>
        </div>

        {/* Right: Live Agentic Console & Sequence Stepper */}
        <aside className="agentic-console-panel">
          <div className="console-title">
            <Sparkles size={15} strokeWidth={1.25} />
            <span>Agentic Sequence Stepper</span>
          </div>

          <div className="workflow-steps-list">
            <div
              className={`workflow-step-card ${
                activeStep === 1 ? "is-active" : activeStep > 1 ? "is-completed" : ""
              }`}
            >
              <div className="step-indicator">01</div>
              <div className="step-details">
                <span className="step-name">Silence Scanner & Laser Splice</span>
                <span className="step-desc">
                  Local pydub silence detector cuts dead-air hesitations and ripples the timeline.
                </span>
              </div>
            </div>

            <div
              className={`workflow-step-card ${
                activeStep === 2 ? "is-active" : activeStep > 2 ? "is-completed" : ""
              }`}
            >
              <div className="step-indicator">02</div>
              <div className="step-details">
                <span className="step-name">Romanized Hinglish Subtitles</span>
                <span className="step-desc">
                  Saaras v4 STT generates millisecond-level word tokens for karaoke captions.
                </span>
              </div>
            </div>

            <div
              className={`workflow-step-card ${
                activeStep === 3 ? "is-active" : activeStep > 3 ? "is-completed" : ""
              }`}
            >
              <div className="step-indicator">03</div>
              <div className="step-details">
                <span className="step-name">Dynamic Indian Sticker Engine</span>
                <span className="step-desc">
                  DuckDuckGo image scrape + rembg transparent PNG background removal.
                </span>
              </div>
            </div>

            <div
              className={`workflow-step-card ${
                activeStep === 4 ? "is-active" : activeStep > 4 ? "is-completed" : ""
              }`}
            >
              <div className="step-indicator">04</div>
              <div className="step-details">
                <span className="step-name">Meme SFX & Keyframe Zooms</span>
                <span className="step-desc">
                  Injects punch-in zooms and comedic sound effects into audio tracks.
                </span>
              </div>
            </div>
          </div>

          <div className="agent-live-log">
            <div className="log-entry">
              <Clock size={11} strokeWidth={1.25} />
              <span>Pipeline: Saaras v4 + Sarvam-105B</span>
            </div>
            <div className={`log-entry ${workflowState === "running" ? "is-highlight" : ""}`}>
              <Zap size={11} strokeWidth={1.25} />
              <span>Status: {currentTaskLabel}</span>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
