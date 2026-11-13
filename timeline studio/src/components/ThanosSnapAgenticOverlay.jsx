import React, { useEffect, useRef, useState, useCallback } from "react";
import {
  Zap,
  Sparkles,
  RotateCcw,
  Clock,
  Layers,
  Cpu,
  Flame,
  Check,
  X,
} from "lucide-react";

export function ThanosSnapAgenticOverlay({
  active = false,
  onClose,
  onApplyEdits,
  timelineDuration = 10,
  t = (k, fallback) => fallback || k,
}) {
  const canvasRef = useRef(null);
  const animationFrameRef = useRef(null);
  const particlesRef = useRef([]);

  // Sequence state
  const [sequenceStep, setSequenceStep] = useState("idle"); // "idle" | "running" | "completed"
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [agentStatus, setAgentStatus] = useState("Sarvam Agent Ready");

  // Ingestion elements displayed in the floating agentic tray
  const [elements, setElements] = useState([
    {
      id: "thanos-raw-video",
      title: "Raw 9:16 Footage",
      sub: "Dead-air at 3.15s - 5.40s",
      type: "video",
      state: "ready", // "ready" | "snapped"
    },
    {
      id: "thanos-captions",
      title: "Romanized Hinglish Subtitles",
      sub: "Saaras v4 word-level timestamps",
      type: "caption",
      state: "ready",
    },
    {
      id: "thanos-sticker",
      title: "Zomato Brand Sticker",
      sub: "rembg Transparent PNG Cutout",
      type: "sticker",
      state: "ready",
    },
    {
      id: "thanos-sfx",
      title: "Vine Boom Meme SFX",
      sub: "Contextual Audio Cue (6.65s)",
      type: "sfx",
      state: "ready",
    },
  ]);

  // Timeline track mock items
  const [isClipSpliced, setIsClipSpliced] = useState(false);
  const [isDeadAirSnapped, setIsDeadAirSnapped] = useState(false);
  const [isRippled, setIsRippled] = useState(false);
  const [materializedItems, setMaterializedItems] = useState([]);

  // Thanos Snap Particle Explosion Generator
  const triggerThanosSnap = useCallback((sourceEl, targetEl, options = {}) => {
    const canvas = canvasRef.current;
    if (!canvas || !sourceEl) return;

    const canvasRect = canvas.getBoundingClientRect();
    const sRect = sourceEl.getBoundingClientRect();

    let targetX = canvasRect.width / 2;
    let targetY = canvasRect.height - 180;

    if (targetEl) {
      const tRect = targetEl.getBoundingClientRect();
      targetX = tRect.left + tRect.width / 2 - canvasRect.left;
      targetY = tRect.top + tRect.height / 2 - canvasRect.top;
    }

    const startX = sRect.left - canvasRect.left;
    const startY = sRect.top - canvasRect.top;
    const width = sRect.width;
    const height = sRect.height;

    // Authentic Thanos Snap Color Spectrum:
    // Cinder embers (bright orange, fiery gold) + cosmic ash (charcoal, slate, ash grey)
    const ashPalette = [
      "#ff5722", // burning cinder
      "#ff9800", // hot ember
      "#ffd54f", // glowing spark
      "#292524", // dark ash flake
      "#44403c", // medium ash
      "#78716c", // drifting dust
      "#e05638", // DaVinci burnt orange
    ];

    // Spawn 280-450 fine ash/cinder particles distributed across the disintegrating card
    const count = options.count || 320;
    for (let i = 0; i < count; i++) {
      // Linear peel effect from left to right
      const relX = Math.random();
      const relY = Math.random();
      const px = startX + relX * width;
      const py = startY + relY * height;

      // Peel delay based on horizontal position (creates the ash wave)
      const peelDelay = relX * 22;

      const pColor = ashPalette[Math.floor(Math.random() * ashPalette.length)];
      const size = Math.random() < 0.75 ? 1 + Math.random() * 2 : 2.5 + Math.random() * 2.5;

      particlesRef.current.push({
        x: px,
        y: py,
        startX: px,
        startY: py,
        targetX: targetX + (Math.random() - 0.5) * 80,
        targetY: targetY + (Math.random() - 0.5) * 20,
        color: pColor,
        size,
        alpha: 1,
        // Cosmic wind vector + turbulence
        vx: 1.5 + Math.random() * 3.5,
        vy: -1.2 + (Math.random() - 0.5) * 2.4,
        rot: Math.random() * Math.PI * 2,
        rotSpeed: (Math.random() - 0.5) * 0.2,
        progress: 0,
        speed: 0.016 + Math.random() * 0.014,
        delay: peelDelay,
        age: 0,
        seed: Math.random() * 100,
        isAsh: pColor === "#292524" || pColor === "#44403c" || pColor === "#78716c",
      });
    }
  }, []);

  // 60FPS Canvas Render Loop with Cosmic Wind Physics
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    const resize = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const particles = particlesRef.current;
      const now = performance.now() * 0.003;

      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];

        if (p.delay > 0) {
          p.delay -= 1;
          continue;
        }

        p.age += 1;
        p.progress += p.speed;

        if (p.progress >= 1) {
          particles.splice(i, 1);
          continue;
        }

        const t = p.progress;

        // Thanos snap flight physics:
        // Ash drifts upward with wind turbulence, then curves downward toward target track
        const windX = Math.sin(now + p.seed) * 1.8;
        const windY = Math.cos(now + p.seed * 0.8) * 1.2;

        const cpX = (p.startX + p.targetX) / 2 + windX * 30;
        const cpY = Math.min(p.startY, p.targetY) - 70 + windY * 20;

        // Quadratic bezier trajectory
        p.x = (1 - t) * (1 - t) * p.startX + 2 * (1 - t) * t * cpX + t * t * p.targetX + windX;
        p.y = (1 - t) * (1 - t) * p.startY + 2 * (1 - t) * t * cpY + t * t * p.targetY;

        p.rot += p.rotSpeed;

        // Fade out near arrival
        if (t > 0.85) {
          p.alpha = Math.max(0, (1 - t) / 0.15);
        }

        ctx.save();
        ctx.globalAlpha = p.alpha;
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rot);

        ctx.fillStyle = p.color;
        if (!p.isAsh) {
          ctx.shadowColor = p.color;
          ctx.shadowBlur = 6;
        }

        // Draw irregular ash flakes
        ctx.beginPath();
        if (p.size > 2) {
          ctx.rect(-p.size / 2, -p.size / 2, p.size, p.size * 0.7);
        } else {
          ctx.arc(0, 0, p.size, 0, Math.PI * 2);
        }
        ctx.fill();

        ctx.restore();
      }

      animationFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener("resize", resize);
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    };
  }, []);

  // Run the full automated Thanos Snap agentic edit sequence
  const startThanosSnapSequence = async () => {
    if (sequenceStep === "running") return;
    setSequenceStep("running");
    resetState();

    // 1. Splicing Animation
    setCurrentStepIndex(1);
    setAgentStatus("Local Silence Scanner: Detecting dead-air hesitation at 3.15s - 5.40s...");
    await sleep(1000);

    setAgentStatus("Laser Cutter: Splicing clip at silence boundaries...");
    setIsClipSpliced(true);
    await sleep(800);

    // THANOS SNAP 1: Disintegrate the dead-air slice on the timeline!
    setAgentStatus("Thanos Snap: Disintegrating dead-air hesitation into ash...");
    const deadAirEl = document.getElementById("thanos-dead-air-block");
    if (deadAirEl) {
      triggerThanosSnap(deadAirEl, null, { count: 350 });
    }
    setIsDeadAirSnapped(true);
    await sleep(500);

    // Ripple snap video clips together
    setIsRippled(true);
    setAgentStatus("Magnetic Ripple: Video track seamlessly snapped (-2.25s eliminated)!");
    await sleep(1000);

    // THANOS SNAP 2: Captions Disintegration & Materialization
    setCurrentStepIndex(2);
    setAgentStatus("Saaras v4 STT: Transliterating Romanized Hinglish speech tokens...");
    await sleep(800);

    setAgentStatus("Thanos Snap: Subtitle card turning to ash & materializing on Caption Track C1...");
    snapElementToTrack("thanos-captions", "thanos-track-c1", () => {
      setMaterializedItems((prev) => [
        ...prev,
        { id: "c1", type: "caption", label: "Aaj hum baat karenge • Secret Trick" },
      ]);
    });
    await sleep(1400);

    // THANOS SNAP 3: Dynamic Sticker Disintegration & Materialization
    setCurrentStepIndex(3);
    setAgentStatus("Sarvam-105B Director: Extracting 'Zomato' transparent PNG sticker...");
    await sleep(800);

    setAgentStatus("Thanos Snap: Zomato asset dissolving into cinders & landing on PiP Track S1...");
    snapElementToTrack("thanos-sticker", "thanos-track-s1", () => {
      setMaterializedItems((prev) => [
        ...prev,
        { id: "s1", type: "sticker", label: "Zomato Transparent PNG (x:0.5, y:0.3)" },
      ]);
    });
    await sleep(1400);

    // THANOS SNAP 4: Meme SFX Disintegration & Materialization
    setCurrentStepIndex(4);
    setAgentStatus("Meme Audio Engine: Synchronizing 'vine_boom.mp3' & 1.25x punch-in zoom...");
    await sleep(800);

    setAgentStatus("Thanos Snap: Audio cue dematerializing & locking into Audio Track A1...");
    snapElementToTrack("thanos-sfx", "thanos-track-a1", () => {
      setMaterializedItems((prev) => [
        ...prev,
        { id: "a1", type: "sfx", label: "vine_boom.mp3 (Vol: 0.8) + Zoom 1.25x" },
      ]);
    });
    await sleep(1200);

    // FINISHED!
    setSequenceStep("completed");
    setAgentStatus("Agentic Auto-Edit Completed — All tracks materialized via Thanos Snap!");
  };

  const snapElementToTrack = (elementId, trackId, onLanded) => {
    const sEl = document.getElementById(elementId);
    const tEl = document.getElementById(trackId);

    // Mark card as snapped
    setElements((items) =>
      items.map((item) => (item.id === elementId ? { ...item, state: "snapped" } : item))
    );

    if (sEl && tEl) {
      triggerThanosSnap(sEl, tEl, { count: 320 });
    }

    setTimeout(() => {
      onLanded();
    }, 600);
  };

  const resetState = () => {
    setIsClipSpliced(false);
    setIsDeadAirSnapped(false);
    setIsRippled(false);
    setMaterializedItems([]);
    setElements((items) => items.map((i) => ({ ...i, state: "ready" })));
    particlesRef.current = [];
  };

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  const handleApply = () => {
    if (onApplyEdits) onApplyEdits();
    if (onClose) onClose();
  };

  return (
    <div className="thanos-agentic-stage">
      {/* 2D Canvas for Thanos Ash Particle Physics */}
      <canvas ref={canvasRef} className="thanos-canvas-overlay" />

      {/* Floating Agentic HUD Bar */}
      <div className="thanos-hud-bar">
        <div className="thanos-hud-left">
          <div className="thanos-ember-icon">
            <Flame size={16} strokeWidth={1.5} />
          </div>
          <div className="thanos-hud-info">
            <span className="thanos-hud-title">Agentic Thanos Snap Engine</span>
            <span className="thanos-hud-sub">{agentStatus}</span>
          </div>
        </div>

        <div className="thanos-hud-actions">
          {sequenceStep === "completed" ? (
            <button
              type="button"
              className="thanos-action-btn is-commit"
              onClick={handleApply}
            >
              <Check size={14} strokeWidth={1.5} />
              <span>Apply to Editor Timeline</span>
            </button>
          ) : (
            <button
              type="button"
              className="thanos-action-btn is-primary"
              disabled={sequenceStep === "running"}
              onClick={startThanosSnapSequence}
            >
              <Zap size={14} strokeWidth={1.5} />
              <span>{sequenceStep === "running" ? "Snapping..." : "Execute Thanos Auto-Cut"}</span>
            </button>
          )}

          <button
            type="button"
            className="thanos-action-btn is-secondary"
            disabled={sequenceStep === "running"}
            onClick={() => {
              resetState();
              setSequenceStep("idle");
              setAgentStatus("Sarvam Agent Ready");
            }}
          >
            <RotateCcw size={13} strokeWidth={1.25} />
            <span>Reset</span>
          </button>

          {onClose && (
            <button
              type="button"
              className="thanos-action-btn is-close"
              onClick={onClose}
              title="Close Thanos Agentic View"
              aria-label="Close"
            >
              <X size={14} strokeWidth={1.5} />
            </button>
          )}
        </div>
      </div>

      {/* Main Agentic Visualizer Workspace */}
      <div className="thanos-workspace-grid">
        {/* Top: Raw Elements Ingestion Tray (Thanos snap peeling origin) */}
        <section className="thanos-tray-section">
          <div className="thanos-section-header">
            <div className="thanos-header-label">
              <Cpu size={13} strokeWidth={1.25} />
              <span>Raw Elements (Disintegrate & Snap to Timeline)</span>
            </div>
            <span className="thanos-step-badge">
              {elements.filter((e) => e.state === "ready").length} Ready for Snap
            </span>
          </div>

          <div className="thanos-elements-deck">
            {elements.map((el) => {
              const isSnapped = el.state === "snapped";
              return (
                <div
                  key={el.id}
                  id={el.id}
                  className={`thanos-element-chip is-${el.type} ${
                    isSnapped ? "is-thanos-snapped" : ""
                  }`}
                >
                  <div className="chip-ember-glow" />
                  <div className="chip-content">
                    <span className="chip-title">{el.title}</span>
                    <span className="chip-sub">{el.sub}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Bottom: Animated Splicing & Materialization Timeline */}
        <section className="thanos-timeline-section">
          <div className="thanos-section-header">
            <div className="thanos-header-label">
              <Layers size={13} strokeWidth={1.25} />
              <span>Interactive Multi-Track Construction</span>
            </div>
            <span className="thanos-step-badge">
              {isRippled ? "12.75s (Dead-Air Snapped)" : "15.0s Raw Clip"}
            </span>
          </div>

          <div className="thanos-tracks-stack">
            {/* V1 Video Track with Laser Splicing */}
            <div className="thanos-track-row">
              <span className="thanos-track-tag">V1 Video</span>
              <div id="thanos-track-v1" className="thanos-lane">
                <div className="thanos-video-block clip-a">
                  <span>Clip A [0.0s - 3.15s]</span>
                </div>

                {/* Spliced Dead Air Portion */}
                {isClipSpliced && !isDeadAirSnapped && (
                  <div id="thanos-dead-air-block" className="thanos-dead-air-block">
                    <div className="thanos-laser-beam" />
                    <div className="thanos-spark-core" />
                    <span>Dead Air [3.15s - 5.40s]</span>
                  </div>
                )}

                <div
                  className={`thanos-video-block clip-b ${
                    isRippled ? "is-rippled-shut" : ""
                  }`}
                >
                  <span>Clip B [5.40s - 15.0s]</span>
                </div>
              </div>
            </div>

            {/* C1 Captions Track */}
            <div className="thanos-track-row">
              <span className="thanos-track-tag">C1 Captions</span>
              <div id="thanos-track-c1" className="thanos-lane">
                {materializedItems
                  .filter((i) => i.type === "caption")
                  .map((item) => (
                    <div key={item.id} className="thanos-materialized-item is-caption">
                      <Sparkles size={11} strokeWidth={1.5} />
                      <span>{item.label}</span>
                    </div>
                  ))}
              </div>
            </div>

            {/* S1 Stickers Track */}
            <div className="thanos-track-row">
              <span className="thanos-track-tag">S1 PiP</span>
              <div id="thanos-track-s1" className="thanos-lane">
                {materializedItems
                  .filter((i) => i.type === "sticker")
                  .map((item) => (
                    <div key={item.id} className="thanos-materialized-item is-sticker">
                      <Flame size={11} strokeWidth={1.5} />
                      <span>{item.label}</span>
                    </div>
                  ))}
              </div>
            </div>

            {/* A1 SFX Track */}
            <div className="thanos-track-row">
              <span className="thanos-track-tag">A1 Audio</span>
              <div id="thanos-track-a1" className="thanos-lane">
                {materializedItems
                  .filter((i) => i.type === "sfx")
                  .map((item) => (
                    <div key={item.id} className="thanos-materialized-item is-sfx">
                      <Zap size={11} strokeWidth={1.5} />
                      <span>{item.label}</span>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
