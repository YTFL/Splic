// Reactive Agentic Automation Layer for Auto-Cut
//
// Features:
// • Visible, human-paced Agentic Ghost Cursor (30px SVG pointer) traversing menus & tracks
// • Authentic Thanos Snap Particle Engine:
//   - Explodes from source sidebar menus / asset cards
//   - Streams along curved Bézier trajectories toward exact timeline layer coordinates
//   - Combines into the exact rectangular shape (borders, header, scanlines) of the timeline clip
//   - Solidifies on the track, then dissolves as the real clip mounts
// • Laser blade slicing across video track at playhead cut seams with cinder sparks
// • 100% non-invasive: pointer-events: none, zero synthetic clicks, zero state conflicts.
import { useEffect, useRef, useState } from "react";
import { Zap, Scissors, Smile, Music, Wand2, Type } from "lucide-react";
import "./AutoCutSweep.css";

const ARRIVAL_SELECTOR = ".image-clip, .caption-segment, .sticker-segment, .audio-clip, .timeline-effect-clip";

function formatTime(seconds) {
  const s = Math.max(0, Number(seconds) || 0);
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${(s % 60).toFixed(1).padStart(4, "0")}`;
}

// Computes the exact perimeter, header line, and interior scanlines of a timeline clip
function generateClipShapePoints(targetX, targetY, targetW, targetH, totalParticles = 130) {
  const points = [];
  const w = Math.max(targetW, 44);
  const h = Math.max(targetH, 26);

  // 1. Perimeter borders
  const topCount = Math.min(22, Math.max(8, Math.floor(w / 5)));
  for (let i = 0; i < topCount; i++) {
    points.push({ x: targetX + (i / (topCount - 1 || 1)) * w, y: targetY });
  }
  const bottomCount = topCount;
  for (let i = 0; i < bottomCount; i++) {
    points.push({ x: targetX + (i / (bottomCount - 1 || 1)) * w, y: targetY + h });
  }
  const sideCount = Math.max(3, Math.floor(h / 7));
  for (let i = 1; i < sideCount; i++) {
    points.push({ x: targetX, y: targetY + (i / sideCount) * h });
    points.push({ x: targetX + w, y: targetY + (i / sideCount) * h });
  }

  // 2. Header separator line
  const headerCount = Math.min(14, Math.floor(w / 7));
  const headerY = targetY + Math.min(10, h * 0.32);
  for (let i = 0; i < headerCount; i++) {
    points.push({ x: targetX + (i / (headerCount - 1 || 1)) * w, y: headerY });
  }

  // 3. Interior scanline matrix
  const remaining = Math.max(0, totalParticles - points.length);
  const cols = 12;
  const rows = 4;
  for (let i = 0; i < remaining; i++) {
    const c = i % cols;
    const r = Math.floor(i / cols) % rows;
    const px = targetX + 4 + (c / (cols - 1 || 1)) * (w - 8);
    const py = headerY + 3 + (r / (rows - 1 || 1)) * (h - (headerY - targetY) - 5);
    points.push({ x: px, y: py });
  }

  return points;
}

const ASH_PALETTE = [
  "#ff5722", // burning cinder
  "#ff9800", // hot ember
  "#ffd54f", // glowing spark
  "#e53935", // Splic red
  "#f87171", // light ember
  "#78716c", // drifting dust
  "#44403c", // slate ash
  "#e2e8f0", // white-hot core
];

export function AutoCutSweep({ sweep }) {
  const canvasRef = useRef(null);
  const particlesRef = useRef([]);
  const animFrameRef = useRef(null);

  const [ghostCursor, setGhostCursor] = useState({
    x: -100,
    y: -100,
    visible: false,
    label: "",
    iconType: "zap",
  });

  const [laserBlade, setLaserBlade] = useState({
    x: 0,
    top: 0,
    height: 0,
    visible: false,
  });

  // Spotlight the sidebar menu tab corresponding to current action
  useEffect(() => {
    if (!sweep?.eventType) return undefined;
    const type = sweep.eventType;
    let targetSelector = null;

    if (type === "sticker") targetSelector = '[data-nuance-id="stickers"], [data-nuance-id="media"]';
    else if (type === "sfx") targetSelector = '[data-nuance-id="audio"]';
    else if (type === "effect") targetSelector = '[data-nuance-id="specialEffects"], [data-nuance-id="effects"]';
    else if (type === "caption") targetSelector = '[data-nuance-id="media"]';

    if (!targetSelector) return undefined;
    const el = document.querySelector(targetSelector);
    if (!el) return undefined;

    el.classList.add("agentic-tab-spotlight");
    const timer = window.setTimeout(() => {
      el.classList.remove("agentic-tab-spotlight");
    }, 1100);

    return () => {
      window.clearTimeout(timer);
      el.classList.remove("agentic-tab-spotlight");
    };
  }, [sweep?.eventType, sweep?.flash]);

  // Seam cut flash & laser blade slicing at the playhead
  useEffect(() => {
    if (!sweep?.flash) return undefined;

    const track = document.querySelector(".image-track") || document.querySelector(".tracks");
    const playhead = document.querySelector(".playhead") || document.querySelector(".timeline-cursor");

    if (track) {
      track.classList.remove("auto-cut-seam-flash");
      void track.offsetWidth;
      track.classList.add("auto-cut-seam-flash");
    }

    if (playhead && track) {
      const pRect = playhead.getBoundingClientRect();
      const tRect = track.getBoundingClientRect();
      const cutX = pRect.left + pRect.width / 2;

      setLaserBlade({
        x: cutX,
        top: tRect.top,
        height: tRect.height,
        visible: true,
      });

      // Move ghost cursor to the cut seam
      setGhostCursor({
        x: cutX,
        y: tRect.top + tRect.height / 2,
        visible: true,
        label: "Ripple Cut",
        iconType: "scissors",
      });

      // Spawn Thanos ash explosion along the dead air cut seam
      for (let i = 0; i < 28; i++) {
        particlesRef.current.push({
          x: cutX + (Math.random() - 0.5) * 6,
          y: tRect.top + Math.random() * tRect.height,
          vx: (Math.random() - 0.5) * 5,
          vy: -1.2 + (Math.random() - 0.5) * 3,
          color: ASH_PALETTE[Math.floor(Math.random() * ASH_PALETTE.length)],
          alpha: 1,
          size: Math.random() * 2.8 + 1.2,
          life: 36,
          isAshDisintegrate: true,
        });
      }

      const bladeTimer = window.setTimeout(() => {
        setLaserBlade((prev) => ({ ...prev, visible: false }));
      }, 550);

      const cursorTimer = window.setTimeout(() => {
        setGhostCursor((prev) => ({ ...prev, visible: false }));
      }, 1000);

      return () => {
        window.clearTimeout(bladeTimer);
        window.clearTimeout(cursorTimer);
      };
    }

    return undefined;
  }, [sweep?.flash]);

  // Thanos Snap Shape Assembly Engine: Explodes from source, flows to track, forms clip shape
  useEffect(() => {
    if (!sweep || typeof MutationObserver === "undefined") return undefined;
    const timers = new Set();

    const triggerThanosSnapToTimeline = (sourceEl, targetRect, label, iconType) => {
      let sourceX = 140;
      let sourceY = 220;
      let sourceW = 120;
      let sourceH = 36;

      if (sourceEl) {
        const sRect = sourceEl.getBoundingClientRect();
        sourceX = sRect.left;
        sourceY = sRect.top;
        sourceW = Math.max(sRect.width, 80);
        sourceH = Math.max(sRect.height, 28);
      }

      const targetX = targetRect.left;
      const targetY = targetRect.top;
      const targetW = targetRect.width;
      const targetH = targetRect.height;

      const cpX = (sourceX + targetX) / 2 + (Math.random() - 0.5) * 40;
      const cpY = Math.min(sourceY, targetY) - 75;

      // 1. Move ghost cursor to the source tab / asset card
      setGhostCursor({
        x: sourceX + sourceW / 2,
        y: sourceY + sourceH / 2,
        visible: true,
        label: `Select: ${label}`,
        iconType,
      });

      // 2. Cursor glides to the target timeline track
      const cursorMoveTimer = window.setTimeout(() => {
        setGhostCursor({
          x: targetX + Math.min(targetW / 2, 60),
          y: targetY + targetH / 2,
          visible: true,
          label: `Assemble: ${label}`,
          iconType,
        });
      }, 420);
      timers.add(cursorMoveTimer);

      const cursorFadeTimer = window.setTimeout(() => {
        setGhostCursor((prev) => ({ ...prev, visible: false }));
      }, 1400);
      timers.add(cursorFadeTimer);

      // 3. Compute structural shape points of the timeline clip (perimeter + scanlines)
      const particleCount = 120;
      const shapePoints = generateClipShapePoints(targetX, targetY, targetW, targetH, particleCount);

      // 4. Spawn Thanos Snap ash peeling & cosmic flow particles
      for (let i = 0; i < particleCount; i++) {
        const relX = Math.random();
        const relY = Math.random();
        const startX = sourceX + relX * sourceW;
        const startY = sourceY + relY * sourceH;
        const destPoint = shapePoints[i] || { x: targetX + relX * targetW, y: targetY + relY * targetH };
        const pColor = ASH_PALETTE[Math.floor(Math.random() * ASH_PALETTE.length)];

        particlesRef.current.push({
          x: startX,
          y: startY,
          startX,
          startY,
          targetX: destPoint.x,
          targetY: destPoint.y,
          cpX,
          cpY,
          progress: 0,
          speed: 0.022 + Math.random() * 0.012,
          delay: Math.floor(relX * 18), // linear peel wave from left to right
          color: pColor,
          size: Math.random() < 0.7 ? 2 + Math.random() * 1.5 : 3 + Math.random() * 1.5,
          alpha: 1,
          linger: 22, // holds shape on timeline for ~350ms before dissolving
          isSnapShape: true,
        });
      }
    };

    const handleNewElement = (element) => {
      element.classList.add("auto-cut-arrive");
      const clearTimer = window.setTimeout(() => {
        element.classList.remove("auto-cut-arrive");
        timers.delete(clearTimer);
      }, 1100);
      timers.add(clearTimer);

      const rect = element.getBoundingClientRect();
      if (rect.width <= 0) return;

      if (element.classList.contains("sticker-segment")) {
        const sourceTab = document.querySelector('[data-nuance-id="stickers"]') || document.querySelector('[data-nuance-id="media"]');
        triggerThanosSnapToTimeline(sourceTab, rect, "Sticker", "smile");
      } else if (element.classList.contains("audio-clip")) {
        const sourceTab = document.querySelector('[data-nuance-id="audio"]');
        triggerThanosSnapToTimeline(sourceTab, rect, "Meme SFX", "music");
      } else if (element.classList.contains("timeline-effect-clip")) {
        const sourceTab = document.querySelector('[data-nuance-id="specialEffects"]') || document.querySelector('[data-nuance-id="effects"]');
        triggerThanosSnapToTimeline(sourceTab, rect, "Visual Effect", "wand");
      } else if (element.classList.contains("caption-segment")) {
        const sourceTab = document.querySelector('[data-nuance-id="media"]');
        triggerThanosSnapToTimeline(sourceTab, rect, "Hinglish Caption", "type");
      }
    };

    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (!(node instanceof Element)) continue;
          if (node.matches(ARRIVAL_SELECTOR)) handleNewElement(node);
          node.querySelectorAll?.(ARRIVAL_SELECTOR).forEach(handleNewElement);
        }
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });

    return () => {
      observer.disconnect();
      timers.forEach((t) => window.clearTimeout(t));
    };
  }, [sweep]);

  // 60FPS Micro-Particle Render Loop: Explosion -> Bézier Arc -> Shape Solidification -> Dissolve
  useEffect(() => {
    if (!sweep) {
      particlesRef.current = [];
      return undefined;
    }

    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const ctx = canvas.getContext("2d");
    if (!ctx) return undefined;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const particles = particlesRef.current;

      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];

        if (p.delay && p.delay > 0) {
          p.delay -= 1;
          continue;
        }

        if (p.isSnapShape) {
          if (p.progress < 1) {
            // Flight phase along quadratic Bézier curve
            p.progress += p.speed;
            if (p.progress > 1) p.progress = 1;

            const t = p.progress;
            const u = 1 - t;
            p.x = u * u * p.startX + 2 * u * t * p.cpX + t * t * p.targetX;
            p.y = u * u * p.startY + 2 * u * t * p.cpY + t * t * p.targetY;
            p.alpha = t < 0.2 ? t / 0.2 : 0.95;
          } else {
            // Shape Solidification Phase: locked into exact clip geometry coordinates
            p.x = p.targetX;
            p.y = p.targetY;
            p.linger -= 1;

            if (p.linger <= 10) {
              p.alpha = Math.max(0, p.linger / 10);
            } else {
              p.alpha = 0.95;
            }

            if (p.linger <= 0) {
              particles.splice(i, 1);
              continue;
            }
          }
        } else if (p.isAshDisintegrate) {
          // Dead air cut seam ash explosion
          p.x += p.vx;
          p.y += p.vy;
          p.vy += 0.08; // subtle gravity
          p.life -= 1;
          p.alpha = Math.max(0, p.life / 36);
          if (p.life <= 0) {
            particles.splice(i, 1);
            continue;
          }
        }

        ctx.fillStyle = p.color;
        ctx.globalAlpha = Math.max(0, Math.min(1, p.alpha));
        ctx.fillRect(Math.round(p.x), Math.round(p.y), Math.round(p.size), Math.round(p.size));
      }

      ctx.globalAlpha = 1;
      animFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener("resize", resize);
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [sweep]);

  if (!sweep) return null;

  const renderCursorIcon = () => {
    switch (ghostCursor.iconType) {
      case "scissors": return <Scissors size={12} strokeWidth={1.5} />;
      case "smile": return <Smile size={12} strokeWidth={1.5} />;
      case "music": return <Music size={12} strokeWidth={1.5} />;
      case "wand": return <Wand2 size={12} strokeWidth={1.5} />;
      case "type": return <Type size={12} strokeWidth={1.5} />;
      default: return <Zap size={12} strokeWidth={1.5} />;
    }
  };

  return (
    <div className="agentic-reactive-overlay" aria-hidden="true">
      {/* Thanos snap & shape assembly particle canvas */}
      <canvas ref={canvasRef} className="agentic-flight-canvas" />

      {/* Laser blade slicing line at playhead seam */}
      {laserBlade.visible && (
        <div
          className="agentic-laser-blade"
          style={{
            left: `${laserBlade.x}px`,
            top: `${laserBlade.top}px`,
            height: `${laserBlade.height}px`,
          }}
        >
          <div className="laser-beam-line" />
          <span className="laser-spark spark-top" />
          <span className="laser-spark spark-mid" />
          <span className="laser-spark spark-bot" />
        </div>
      )}

      {/* Prominent Agentic Ghost Cursor (30px) */}
      {ghostCursor.visible && (
        <div
          className="agentic-ghost-cursor"
          style={{
            transform: `translate(${ghostCursor.x}px, ${ghostCursor.y}px)`,
          }}
        >
          <svg className="ghost-pointer-svg" width="30" height="30" viewBox="0 0 24 24" fill="none">
            <path
              d="M3 3L10.07 20.97L13.58 13.58L20.97 10.07L3 3Z"
              fill="#e53935"
              stroke="#ffffff"
              strokeWidth="2"
              strokeLinejoin="round"
            />
          </svg>
          <div className="ghost-focus-ring" />
          {ghostCursor.label && (
            <div className="ghost-action-tag">
              <span className="ghost-tag-icon">{renderCursorIcon()}</span>
              <span className="ghost-tag-text">{ghostCursor.label}</span>
            </div>
          )}
        </div>
      )}

      {/* Status Pill with Live Timecode */}
      <div className="assembly-status-pill auto-cut-sweep-pill" role="status" aria-live="polite">
        <div className="assembly-pulse-icon">
          <Zap size={13} strokeWidth={1.5} />
        </div>
        <span>{sweep.text}</span>
        {sweep.total > 0 ? (
          <span className="auto-cut-sweep-time">
            {formatTime(sweep.time)} / {formatTime(sweep.total)}
          </span>
        ) : null}
      </div>
    </div>
  );
}
