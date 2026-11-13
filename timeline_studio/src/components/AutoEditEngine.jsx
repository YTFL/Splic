import React, { useEffect, useRef, useState, useCallback } from "react";
import { Zap } from "lucide-react";
import { normalizeEditPlan } from "../lib/editPlanEngine.js";

// Generates structural geometry points mapping the exact rectangle and interior scanlines of a timeline clip
function generateClipShapePoints(targetX, targetY, targetW, targetH, totalParticles = 200) {
  const points = [];

  // 1. Perimeter borders: top, bottom, left, right
  const topCount = 24;
  for (let i = 0; i < topCount; i++) {
    points.push({ x: targetX + (i / (topCount - 1)) * targetW, y: targetY });
  }
  const bottomCount = 24;
  for (let i = 0; i < bottomCount; i++) {
    points.push({ x: targetX + (i / (bottomCount - 1)) * targetW, y: targetY + targetH });
  }
  const sideCount = 6;
  for (let i = 1; i < sideCount; i++) {
    points.push({ x: targetX, y: targetY + (i / sideCount) * targetH });
    points.push({ x: targetX + targetW, y: targetY + (i / sideCount) * targetH });
  }

  // 2. Header separator line
  const headerCount = 16;
  const headerY = targetY + Math.min(13, targetH * 0.3);
  for (let i = 0; i < headerCount; i++) {
    points.push({ x: targetX + (i / (headerCount - 1)) * targetW, y: headerY });
  }

  // 3. Interior scanline matrix
  const cols = 22;
  const rows = 6;
  const interiorCount = totalParticles - points.length;
  for (let i = 0; i < interiorCount; i++) {
    const c = i % cols;
    const r = Math.floor(i / cols) % rows;
    const px = targetX + 4 + (c / (cols - 1 || 1)) * (targetW - 8);
    const py = headerY + 3 + (r / (rows - 1 || 1)) * (targetH - (headerY - targetY) - 5);
    points.push({ x: px, y: py });
  }

  return points;
}

// Queries the REAL DOM elements for the timeline tracks to guarantee 1:1 pixel alignment
function getTimelineLayout() {
  const imageTrack = document.querySelector(".image-track") || document.querySelector(".tracks");
  const overlayTrack = document.querySelector(".visual-overlay-track") || document.querySelector(".sticker-track");
  const effectLane = document.querySelector(".timeline-effect-lane") || document.querySelector(".effects-track");
  const audioTrack = document.querySelector(".audio-track.music-track") || document.querySelector(".audio-track");

  let imgRect = { left: 260, top: window.innerHeight - 190, width: 700, height: 48 };
  if (imageTrack) {
    const r = imageTrack.getBoundingClientRect();
    if (r.width > 50 && r.height > 20) {
      imgRect = { left: r.left, top: r.top, width: r.width, height: r.height };
    }
  }

  // Row 1: Sticker / Overlay Layer (immediately below Media Track)
  let overlayTop = imgRect.top + imgRect.height + 4;
  let overlayHeight = 38;
  if (overlayTrack) {
    const r = overlayTrack.getBoundingClientRect();
    if (r.width > 50) {
      overlayTop = r.top;
      overlayHeight = r.height;
    }
  }

  // Row 2: Special Effects Layer (immediately below Overlay Track)
  let effectTop = overlayTop + overlayHeight + 4;
  let effectHeight = 36;
  if (effectLane) {
    const r = effectLane.getBoundingClientRect();
    if (r.width > 50) {
      effectTop = r.top;
      effectHeight = r.height;
    }
  }

  // Row 3: Audio & SFX Layer (at the bottom of track scroll)
  let audioTop = effectTop + effectHeight + 36;
  let audioHeight = 40;
  if (audioTrack) {
    const r = audioTrack.getBoundingClientRect();
    if (r.width > 50) {
      audioTop = r.top;
      audioHeight = r.height;
    }
  }

  return {
    imageTrack: imgRect,
    overlayTrack: { left: imgRect.left, top: overlayTop, width: imgRect.width, height: overlayHeight },
    effectTrack: { left: imgRect.left, top: effectTop, width: imgRect.width, height: effectHeight },
    audioTrack: { left: imgRect.left, top: audioTop, width: imgRect.width, height: audioHeight },
  };
}

// Computes the pixel geometry of all clips directly on the real track lines
function computeClipGeometry(plan, layout) {
  const img = layout.imageTrack;
  const overlay = layout.overlayTrack;
  const effects = layout.effectTrack;
  const audio = layout.audioTrack;

  const duration1 = plan.media?.cut1?.duration || 3.15;
  const duration2 = plan.media?.cut2?.duration || 4.2;
  const viewportW = Math.max(400, Math.min(img.width, window.innerWidth - img.left - 48));
  const totalDuration = duration1 + duration2;
  const gapW = 80;
  const usableW = Math.min(viewportW - gapW, 600);

  const cut1W = Math.max(170, Math.round((duration1 / totalDuration) * usableW));
  const cut2W = Math.max(190, usableW - cut1W);

  // Row 0: Media Footage Layer (V1)
  const cut1X = img.left;
  const cut1Y = img.top;
  const cut1H = img.height;

  const deadAirX = cut1X + cut1W;
  const deadAirY = cut1Y;
  const deadAirW = gapW;
  const deadAirH = cut1H;

  const cut2PreX = deadAirX + deadAirW;
  const cut2PostX = cut1X + cut1W;
  const cut2Y = cut1Y;
  const cut2H = cut1H;

  // Row 1: Sticker / Overlay Layer (V2)
  const overlayX = img.left + Math.round(cut1W * 0.35);
  const overlayY = overlay.top;
  const overlayW = 150;
  const overlayH = overlay.height;

  // Row 2: Special Effects Layer (FX)
  const effectX = img.left + Math.max(0, cut1W - 50);
  const effectY = effects.top;
  const effectW = 130;
  const effectH = effects.height;

  // Row 3: Audio & SFX Layer (A1)
  const audioX = img.left + cut1W + 10;
  const audioY = audio.top;
  const audioW = 140;
  const audioH = audio.height;

  return {
    cut1: { x: cut1X, y: cut1Y, w: cut1W, h: cut1H },
    deadAir: { x: deadAirX, y: deadAirY, w: deadAirW, h: deadAirH },
    cut2Pre: { x: cut2PreX, y: cut2Y, w: cut2W, h: cut2H },
    cut2Post: { x: cut2PostX, y: cut2Y, w: cut2W, h: cut2H },
    overlay: { x: overlayX, y: overlayY, w: overlayW, h: overlayH },
    effects: { x: effectX, y: effectY, w: effectW, h: effectH },
    audio: { x: audioX, y: audioY, w: audioW, h: audioH },
  };
}

export function AutoEditEngine({
  running = false,
  sessionId = 0,
  hasExistingTimeline = false,
  userAssets = [],
  editPlanInput = null,
  onSelectTool,
  onResetTimeline,
  onComplete,
  onCommitTimeline,
}) {
  const canvasRef = useRef(null);
  const animationFrameRef = useRef(null);
  const particlesRef = useRef([]);

  const isExecutingRef = useRef(false);
  const editPlanInputRef = useRef(editPlanInput);
  const onSelectToolRef = useRef(onSelectTool);
  const onResetTimelineRef = useRef(onResetTimeline);
  const onCommitTimelineRef = useRef(onCommitTimeline);
  const onCompleteRef = useRef(onComplete);
  const hasExistingTimelineRef = useRef(hasExistingTimeline);

  useEffect(() => {
    editPlanInputRef.current = editPlanInput;
  }, [editPlanInput]);

  useEffect(() => {
    onSelectToolRef.current = onSelectTool;
  }, [onSelectTool]);

  useEffect(() => {
    onResetTimelineRef.current = onResetTimeline;
  }, [onResetTimeline]);

  useEffect(() => {
    onCommitTimelineRef.current = onCommitTimeline;
  }, [onCommitTimeline]);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    hasExistingTimelineRef.current = hasExistingTimeline;
  }, [hasExistingTimeline]);

  // Animation phases
  const [phase, setPhase] = useState("idle");
  const [statusText, setStatusText] = useState("");
  const [currentPlan, setCurrentPlan] = useState(null);
  const [clipGeometry, setClipGeometry] = useState(null);
  const [currentPresence, setCurrentPresence] = useState("none");

  // Multi-Track Live Visual State (Media, Sticker, Effects, Audio)
  const [timelineTracks, setTimelineTracks] = useState({
    cut1Merged: false,
    cut2Merged: false,
    silenceDetected: false,
    isSplicing: false,
    gapClosed: false,
    effectsMerged: false,
    overlayMerged: false,
    audioMerged: false,
  });

  // 60FPS Minimal Pixel Canvas Loop (ZERO BLOOM, realistic micro-particles)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.shadowBlur = 0;
      ctx.shadowColor = "transparent";

      const particles = particlesRef.current;
      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];

        if (p.delay > 0) {
          p.delay -= 1;
          continue;
        }

        if (p.isCollapsing) {
          p.x += p.vx;
          p.y += p.vy;
          p.vy += 0.08;
          p.alpha -= 0.035;
          if (p.alpha <= 0) {
            particles.splice(i, 1);
            continue;
          }
          ctx.fillStyle = p.color;
          ctx.globalAlpha = Math.max(0, p.alpha);
          ctx.fillRect(Math.round(p.x), Math.round(p.y), Math.round(p.size), Math.round(p.size));
          continue;
        }

        // Forward trajectory from source to timeline clip coordinates
        if (p.progress < 1) {
          p.progress += p.speed;
          if (p.progress > 1) p.progress = 1;

          const tVal = p.progress;
          const u = 1 - tVal;
          const tt = tVal * tVal;
          const uu = u * u;

          p.x = uu * p.startX + 2 * u * tVal * p.cpX + tt * p.targetX;
          p.y = uu * p.startY + 2 * u * tVal * p.cpY + tt * p.targetY;

          if (tVal < 0.2) {
            p.alpha = tVal / 0.2;
          } else if (tVal > 0.85) {
            p.alpha = 1;
          } else {
            p.alpha = 0.95;
          }
        } else {
          // Assembled on timeline: holds exact shape coordinates
          p.x = p.targetX;
          p.y = p.targetY;

          if (!p.hasTriggeredMerge && p.onMerged) {
            p.hasTriggeredMerge = true;
            p.onMerged();
          }

          p.linger -= 1;
          if (p.linger <= 14) {
            p.alpha = Math.max(0, p.linger / 14);
          } else {
            p.alpha = 0.95;
          }

          if (p.linger <= 0) {
            particles.splice(i, 1);
            continue;
          }
        }

        ctx.fillStyle = p.color;
        ctx.globalAlpha = Math.max(0, Math.min(1, p.alpha));
        ctx.fillRect(Math.round(p.x), Math.round(p.y), Math.round(p.size), Math.round(p.size));
      }

      ctx.globalAlpha = 1;
      animationFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener("resize", resize);
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    };
  }, []);

  // Collapse specific UI element and stream particles directly into its assigned timeline track coordinates
  const collapseAndStreamToTimeline = useCallback((asset, assetIndex, targetConfig, options = {}) => {
    return new Promise((resolve) => {
      let sourceLeft = 140;
      let sourceTop = 200 + assetIndex * 48;
      let sourceWidth = 140;
      let sourceHeight = 40;

      let targetEl = null;
      if (options.selector) {
        targetEl = document.querySelector(options.selector);
      }
      if (!targetEl && asset?.id) {
        targetEl = document.getElementById(`media-pool-asset-${asset.id}`);
      }
      if (!targetEl) {
        const rows = document.querySelectorAll(".asset-row-wrap");
        targetEl = rows[assetIndex] || rows[0];
      }
      if (!targetEl) {
        targetEl = document.querySelector(".media-panel") || document.querySelector(".drop-zone");
      }

      if (targetEl) {
        const rect = targetEl.getBoundingClientRect();
        sourceLeft = rect.left;
        sourceTop = rect.top;
        sourceWidth = Math.max(rect.width, 100);
        sourceHeight = Math.max(rect.height, 32);

        targetEl.classList.add("is-collapsing-thumbnail");
      }

      const targetX = targetConfig.x;
      const targetY = targetConfig.y;
      const targetW = targetConfig.w;
      const targetH = targetConfig.h;

      const cpX = (sourceLeft + targetX) / 2 + (Math.random() - 0.5) * 30;
      const cpY = Math.min(sourceTop, targetY) - 95;

      const colors = targetConfig.colors || ["#d59b72", "#bc7c4f", "#8b5a3c", "#3e3b38"];
      const particleCount = options.particleCount || 200;
      const shapePoints = generateClipShapePoints(targetX, targetY, targetW, targetH, particleCount);

      for (let i = 0; i < particleCount; i++) {
        const startX = sourceLeft + Math.random() * sourceWidth;
        const startY = sourceTop + Math.random() * sourceHeight;
        const destPoint = shapePoints[i] || { x: targetX + Math.random() * targetW, y: targetY + Math.random() * targetH };
        const pColor = colors[Math.floor(Math.random() * colors.length)];

        particlesRef.current.push({
          x: startX,
          y: startY,
          startX,
          startY,
          targetX: destPoint.x,
          targetY: destPoint.y,
          cpX,
          cpY,
          seed: Math.random() * 100,
          color: pColor,
          size: 1.0 + Math.random() * 0.8,
          alpha: 0,
          progress: 0,
          speed: 0.022 + Math.random() * 0.014,
          delay: Math.random() * 12,
          linger: 42,
          hasTriggeredMerge: false,
          onMerged: targetConfig.onMerged,
        });
      }

      setTimeout(() => {
        resolve();
      }, 1120);
    });
  }, []);

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  // Main Orchestration Sequence — Plays agentic animation sequence based on JSON file instructions
  useEffect(() => {
    if (!running) {
      isExecutingRef.current = false;
      setPhase("idle");
      setCurrentPresence("none");
      setClipGeometry(null);
      setTimelineTracks({
        cut1Merged: false,
        cut2Merged: false,
        silenceDetected: false,
        isSplicing: false,
        gapClosed: false,
        effectsMerged: false,
        overlayMerged: false,
        audioMerged: false,
      });

      document.querySelectorAll(".is-collapsing-thumbnail, .is-agentic-selected-card").forEach((el) => {
        el.classList.remove("is-collapsing-thumbnail", "is-agentic-selected-card");
      });
      document.body.classList.remove("is-timeline-collapsing");
      return;
    }

    if (isExecutingRef.current) return;
    isExecutingRef.current = true;

    let isCancelled = false;

    const executeAgenticAutoEdit = async () => {
      // 0. Clean slate collapse if previous timeline exists
      if (hasExistingTimelineRef.current) {
        setPhase("timeline-collapse");
        setStatusText("Collapsing existing timeline — Clearing slate for fresh edit...");
        document.body.classList.add("is-timeline-collapsing");

        const existingClips = document.querySelectorAll(
          ".merged-track-clip, .timeline-board .image-clip, .silence-dead-air-gap, .transition-seam-badge"
        );
        existingClips.forEach((el) => {
          const rect = el.getBoundingClientRect();
          const pColors = ["#8b5a3c", "#584236", "#a06d4e", "#3a3430"];
          for (let k = 0; k < 25; k++) {
            particlesRef.current.push({
              x: rect.left + Math.random() * rect.width,
              y: rect.top + Math.random() * rect.height,
              vx: (rect.left - (rect.left + Math.random() * rect.width)) * 0.05,
              vy: (Math.random() - 0.5) * 1.5,
              alpha: 0.9,
              size: 1.1 + Math.random() * 0.8,
              color: pColors[Math.floor(Math.random() * pColors.length)],
              isCollapsing: true,
            });
          }
        });

        await sleep(420);
        if (isCancelled) return;

        if (onResetTimelineRef.current) {
          onResetTimelineRef.current();
        }

        setTimelineTracks({
          cut1Merged: false,
          cut2Merged: false,
          silenceDetected: false,
          isSplicing: false,
          gapClosed: false,
          effectsMerged: false,
          overlayMerged: false,
          audioMerged: false,
        });

        document.querySelectorAll(".is-collapsing-thumbnail, .is-agentic-selected-card").forEach((el) => {
          el.classList.remove("is-collapsing-thumbnail", "is-agentic-selected-card");
        });

        document.body.classList.remove("is-timeline-collapsing");
        await sleep(200);
        if (isCancelled) return;
      }

      // 1. Ingest JSON EditPlan (file, string, or object) and normalize instructions
      let plan;
      try {
        plan = normalizeEditPlan(editPlanInputRef.current, userAssets);
      } catch {
        plan = normalizeEditPlan(null, userAssets);
      }
      setCurrentPlan(plan);

      if (onSelectToolRef.current) {
        onSelectToolRef.current("media");
      }

      // 2. Compute 1:1 pixel coordinates on timeline tracks
      const layout = getTimelineLayout();
      const geo = computeClipGeometry(plan, layout);
      setClipGeometry(geo);

      // 3. Acoustic waveform frequency sweep
      setPhase("wave");
      setStatusText("Acoustic analysis: Sarvam Saaras v4 frequency sweep...");
      await sleep(950);
      if (isCancelled) return;

      // 4. STEP 1: Media Cut 1 -> Media Layer (V1 - Row 0)
      setPhase("collapse-media-1");
      setCurrentPresence("cut1");
      setAgenticFocus({
        x: 60,
        y: 190,
        category: "MEDIA POOL",
        title: plan.media.cut1.asset.name,
        action: "Exploding asset particles -> Merging to Media Layer (V1)",
        color: "#d59b72",
      });
      setStatusText(`Agentic Workflow: Collapsing ${plan.media.cut1.asset.name} -> Merging Cut 01 (0.00s)...`);
      await collapseAndStreamToTimeline(plan.media.cut1.asset, plan.media.cut1.assetIndex, {
        x: geo.cut1.x,
        y: geo.cut1.y,
        w: geo.cut1.w,
        h: geo.cut1.h,
        colors: plan.media.cut1.colorPalette,
        onMerged: () => {
          setTimelineTracks((prev) => ({ ...prev, cut1Merged: true }));
          setCurrentPresence("none");
        },
      });
      if (isCancelled) return;
      await sleep(240);

      // 5. STEP 2: Media Cut 2 -> Last part of Media Layer (V1)
      setPhase("collapse-media-2");
      setCurrentPresence("cut2");
      setAgenticFocus({
        x: 60,
        y: 240,
        category: "MEDIA POOL",
        title: plan.media.cut2.asset.name,
        action: "Exploding asset particles -> Streaming to Cut 02 in last part of track",
        color: "#c2653c",
      });
      setStatusText(`Agentic Workflow: Collapsing ${plan.media.cut2.asset.name} -> Streaming to Cut 02...`);
      await collapseAndStreamToTimeline(plan.media.cut2.asset, plan.media.cut2.assetIndex, {
        x: geo.cut2Pre.x,
        y: geo.cut2Pre.y,
        w: geo.cut2Pre.w,
        h: geo.cut2Pre.h,
        colors: plan.media.cut2.colorPalette,
        onMerged: () => {
          setTimelineTracks((prev) => ({
            ...prev,
            cut2Merged: true,
            silenceDetected: true,
          }));
          setCurrentPresence("none");
        },
      });
      if (isCancelled) return;
      await sleep(300);

      // 6. Laser blade splicing dead air and magnetic ripple closure
      setPhase("splicing");
      setAgenticFocus(null);
      setStatusText(`Laser blade splicing dead-air silence at ${plan.media.cut1.duration}s...`);
      setTimelineTracks((prev) => ({ ...prev, isSplicing: true }));
      await sleep(550);
      if (isCancelled) return;

      setStatusText("Magnetic ripple snap: Sealing gap and joining video cuts...");
      setTimelineTracks((prev) => ({ ...prev, gapClosed: true, isSplicing: false }));
      await sleep(750);
      if (isCancelled) return;

      // 7. STEP 3: Special Effects Layer (Row 2) - Selection based on JSON effect
      setPhase("agentic-effects");
      if (onSelectToolRef.current) {
        onSelectToolRef.current("specialEffects");
      }
      await sleep(250);
      if (isCancelled) return;

      const effectCard =
        document.querySelector(`.timeline-effect-card[data-effect='${plan.effect.effect}']`) ||
        document.querySelector(".timeline-effect-card");
      if (effectCard) {
        effectCard.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
        effectCard.classList.add("is-agentic-selected-card");
      }
      await sleep(350);
      if (isCancelled) return;

      setPhase("collapse-effects");
      setCurrentPresence("effects");
      await collapseAndStreamToTimeline(
        plan.effect,
        1,
        {
          x: geo.effects.x,
          y: geo.effects.y,
          w: geo.effects.w,
          h: geo.effects.h,
          colors: plan.effect.colorPalette,
          onMerged: () => {
            setTimelineTracks((prev) => ({ ...prev, effectsMerged: true }));
            setCurrentPresence("none");
          },
        },
        {
          selector: `.timeline-effect-card[data-effect='${plan.effect.effect}'], .timeline-effect-card.is-agentic-selected-card, .timeline-effect-card`,
          particleCount: 160,
        }
      );
      if (isCancelled) return;
      await sleep(240);

      // 8. STEP 4: Dynamic Stickers Layer (Row 1 - V2) from JSON
      setPhase("collapse-sticker");
      setCurrentPresence("sticker");
      await collapseAndStreamToTimeline(
        plan.sticker.asset,
        plan.sticker.assetIndex,
        {
          x: geo.overlay.x,
          y: geo.overlay.y,
          w: geo.overlay.w,
          h: geo.overlay.h,
          colors: plan.sticker.colorPalette,
          onMerged: () => {
            setTimelineTracks((prev) => ({ ...prev, overlayMerged: true }));
            setCurrentPresence("none");
          },
        },
        {
          selector: ".davinci-nuances-nav [role='tab']:nth-child(6)",
        }
      );
      if (isCancelled) return;
      await sleep(240);

      // 9. STEP 5: Meme SFX Audio Layer (Row 3 - A1) from JSON
      setPhase("collapse-audio");
      setCurrentPresence("audio");
      await collapseAndStreamToTimeline(
        plan.audio.asset,
        plan.audio.assetIndex,
        {
          x: geo.audio.x,
          y: geo.audio.y,
          w: geo.audio.w,
          h: geo.audio.h,
          colors: plan.audio.colorPalette,
          onMerged: () => {
            setTimelineTracks((prev) => ({ ...prev, audioMerged: true }));
            setCurrentPresence("none");
          },
        },
        {
          selector: ".davinci-nuances-nav [role='tab']:nth-child(4)",
        }
      );
      if (isCancelled) return;
      await sleep(350);

      // 10. Commit plan to Timeline Studio
      setPhase("done");

      if (onCommitTimelineRef.current) {
        onCommitTimelineRef.current({
          ...plan,
          cut1: plan.media.cut1,
          cut2: plan.media.cut2,
        });
      }

      await sleep(350);
      if (isCancelled) return;

      setPhase("idle");
      isExecutingRef.current = false;
      if (onCompleteRef.current) {
        onCompleteRef.current();
      }
    };

    executeAgenticAutoEdit();

    return () => {
      isCancelled = true;
    };
  }, [running, sessionId, userAssets, collapseAndStreamToTimeline]);

  const geo = clipGeometry;

  return (
    <>
      {/* 60FPS Minimal Particle Canvas */}
      <canvas
        ref={canvasRef}
        className="auto-edit-canvas"
        style={{
          position: "fixed",
          inset: 0,
          pointerEvents: "none",
          zIndex: 9998,
          display: running ? "block" : "none",
        }}
      />

      {running && geo && (
        <div className="auto-edit-hud-layer" style={{ position: "fixed", inset: 0, pointerEvents: "none", zIndex: 9999 }}>
          {/* Wave Sweep Banner */}
          {phase === "wave" && (
            <div className="acoustic-wave-indicator">
              <span className="wave-pulse-ring" />
              <span className="wave-title">{statusText}</span>
            </div>
          )}

          {/* Splicing Laser Blade */}
          {timelineTracks.isSplicing && (
            <div
              className="timeline-laser-blade"
              style={{
                position: "fixed",
                left: `${geo.cut1.x + geo.cut1.w}px`,
                top: `${geo.cut1.y - 14}px`,
                height: `${geo.cut1.h + 28}px`,
              }}
            >
              <div className="laser-beam-line" />
              <span className="laser-spark-particle spark-1" />
              <span className="laser-spark-particle spark-2" />
              <span className="laser-spark-particle spark-3" />
            </div>
          )}

          {/* =========================================================================
              ROW 0: MEDIA FOOTAGE LAYER (V1)
              ========================================================================= */}
          <div
            className="track-layer-header-pill layer-media"
            style={{ position: "fixed", left: `${geo.cut1.x}px`, top: `${geo.cut1.y - 12}px` }}
          >
            <span>V1 · MEDIA FOOTAGE</span>
          </div>

          {currentPresence === "cut1" && !timelineTracks.cut1Merged && (
            <div
              className="timeline-presence-slot"
              style={{
                position: "fixed",
                left: `${geo.cut1.x}px`,
                top: `${geo.cut1.y}px`,
                width: `${geo.cut1.w}px`,
                height: `${geo.cut1.h}px`,
                borderColor: "#d59b72",
              }}
            >
              <span className="presence-label">PRESENCE · CUT 01</span>
              <span className="presence-time">0.00s — {currentPlan?.media?.cut1?.duration || "3.15"}s</span>
            </div>
          )}

          {timelineTracks.cut1Merged && (
            <div
              className="merged-track-clip clip-cut-1"
              style={{
                position: "fixed",
                left: `${geo.cut1.x}px`,
                top: `${geo.cut1.y}px`,
                width: `${geo.cut1.w}px`,
                height: `${geo.cut1.h}px`,
              }}
            >
              <span className="clip-tag">{currentPlan?.media?.cut1?.name || "Main Footage [Part 01]"}</span>
              <span className="clip-time">0.00s — {currentPlan?.media?.cut1?.duration || "3.15"}s</span>
            </div>
          )}

          {/* Dead-Air Silence Gap */}
          {timelineTracks.cut1Merged && !timelineTracks.gapClosed && (
            <div
              className="silence-dead-air-gap"
              style={{
                position: "fixed",
                left: `${geo.deadAir.x}px`,
                top: `${geo.deadAir.y}px`,
                width: `${geo.deadAir.w}px`,
                height: `${geo.deadAir.h}px`,
              }}
            >
              <span className="gap-label">DEAD AIR GAP</span>
              <span className="gap-duration">{currentPlan?.deadAir?.duration || "1.80"}s Silence</span>
            </div>
          )}

          {currentPresence === "cut2" && !timelineTracks.cut2Merged && (
            <div
              className="timeline-presence-slot"
              style={{
                position: "fixed",
                left: `${geo.cut2Pre.x}px`,
                top: `${geo.cut2Pre.y}px`,
                width: `${geo.cut2Pre.w}px`,
                height: `${geo.cut2Pre.h}px`,
                borderColor: "#c2653c",
              }}
            >
              <span className="presence-label">PRESENCE · CUT 02 (PRE-RIPPLE)</span>
              <span className="presence-time">Streaming to track tail</span>
            </div>
          )}

          {timelineTracks.cut2Merged && (
            <div
              className={`merged-track-clip clip-cut-2 ${timelineTracks.gapClosed ? "is-rippled-left" : ""}`}
              style={{
                position: "fixed",
                left: timelineTracks.gapClosed ? `${geo.cut2Post.x}px` : `${geo.cut2Pre.x}px`,
                top: `${geo.cut2Post.y}px`,
                width: `${geo.cut2Post.w}px`,
                height: `${geo.cut2Post.h}px`,
              }}
            >
              <span className="clip-tag">{currentPlan?.media?.cut2?.name || "Main Footage [Part 02]"}</span>
              <span className="clip-time">Duration: {currentPlan?.media?.cut2?.duration || "4.20"}s</span>
            </div>
          )}

          {/* Transition Seam Indicator */}
          {timelineTracks.gapClosed && (
            <div
              className="transition-seam-badge"
              style={{
                position: "fixed",
                left: `${geo.cut1.x + geo.cut1.w - 18}px`,
                top: `${geo.cut1.y + 6}px`,
              }}
            >
              <span className="seam-dot" />
              <span className="seam-label">RIPPLE CUT</span>
            </div>
          )}

          {/* =========================================================================
              ROW 1: STICKER / OVERLAY LAYER (V2)
              ========================================================================= */}
          <div
            className="track-layer-header-pill layer-overlay"
            style={{ position: "fixed", left: `${geo.overlay.x}px`, top: `${geo.overlay.y - 12}px` }}
          >
            <span>V2 · STICKER / OVERLAY</span>
          </div>

          {currentPresence === "sticker" && !timelineTracks.overlayMerged && (
            <div
              className="timeline-presence-slot"
              style={{
                position: "fixed",
                left: `${geo.overlay.x}px`,
                top: `${geo.overlay.y}px`,
                width: `${geo.overlay.w}px`,
                height: `${geo.overlay.h}px`,
                borderColor: "#cb202d",
              }}
            >
              <span className="presence-label" style={{ color: "#e84550" }}>PRESENCE · {currentPlan?.sticker?.keyword || "STICKER"}</span>
              <span className="presence-time">{currentPlan?.sticker?.start || "1.5"}s — {((currentPlan?.sticker?.start || 1.5) + (currentPlan?.sticker?.duration || 2.2)).toFixed(2)}s</span>
            </div>
          )}

          {timelineTracks.overlayMerged && (
            <div
              className="merged-track-clip clip-overlay"
              style={{
                position: "fixed",
                left: `${geo.overlay.x}px`,
                top: `${geo.overlay.y}px`,
                width: `${geo.overlay.w}px`,
                height: `${geo.overlay.h}px`,
              }}
            >
              <span className="clip-tag">{currentPlan?.sticker?.name || "Dynamic Cultural Sticker"}</span>
              <span className="clip-time">Sticker Track · {currentPlan?.sticker?.duration || "2.2"}s</span>
            </div>
          )}

          {/* =========================================================================
              ROW 2: SPECIAL EFFECTS LAYER (FX)
              ========================================================================= */}
          <div
            className="track-layer-header-pill layer-effects"
            style={{ position: "fixed", left: `${geo.effects.x}px`, top: `${geo.effects.y - 12}px` }}
          >
            <span>FX · SPECIAL EFFECTS</span>
          </div>

          {currentPresence === "effects" && !timelineTracks.effectsMerged && (
            <div
              className="timeline-presence-slot"
              style={{
                position: "fixed",
                left: `${geo.effects.x}px`,
                top: `${geo.effects.y}px`,
                width: `${geo.effects.w}px`,
                height: `${geo.effects.h}px`,
                borderColor: currentPlan?.effect?.color || "#f5c542",
              }}
            >
              <span className="presence-label" style={{ color: currentPlan?.effect?.color || "#ffd700" }}>
                PRESENCE · {currentPlan?.effect?.name?.toUpperCase() || "EFFECT"}
              </span>
              <span className="presence-time">{currentPlan?.effect?.start || "2.8"}s</span>
            </div>
          )}

          {timelineTracks.effectsMerged && (
            <div
              className="merged-track-clip clip-effects"
              style={{
                position: "fixed",
                left: `${geo.effects.x}px`,
                top: `${geo.effects.y}px`,
                width: `${geo.effects.w}px`,
                height: `${geo.effects.h}px`,
                borderColor: currentPlan?.effect?.color || "#f5c542",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
                <Zap size={11} strokeWidth={2.5} style={{ color: currentPlan?.effect?.color || "#f5c542" }} />
                <span className="clip-tag">{currentPlan?.effect?.name || "Transition Effect"}</span>
              </div>
              <span className="clip-time">Effects Layer · {currentPlan?.effect?.duration || "1.4"}s</span>
            </div>
          )}

          {/* =========================================================================
              ROW 3: AUDIO & SFX LAYER (A1)
              ========================================================================= */}
          <div
            className="track-layer-header-pill layer-audio"
            style={{ position: "fixed", left: `${geo.audio.x}px`, top: `${geo.audio.y - 12}px` }}
          >
            <span>A1 · AUDIO & SFX</span>
          </div>

          {currentPresence === "audio" && !timelineTracks.audioMerged && (
            <div
              className="timeline-presence-slot"
              style={{
                position: "fixed",
                left: `${geo.audio.x}px`,
                top: `${geo.audio.y}px`,
                width: `${geo.audio.w}px`,
                height: `${geo.audio.h}px`,
                borderColor: "#58a065",
              }}
            >
              <span className="presence-label" style={{ color: "#7fd48e" }}>PRESENCE · SFX BOOM</span>
              <span className="presence-time">{currentPlan?.audio?.duration || "1.6"}s impact</span>
            </div>
          )}

          {timelineTracks.audioMerged && (
            <div
              className="merged-track-clip clip-audio"
              style={{
                position: "fixed",
                left: `${geo.audio.x}px`,
                top: `${geo.audio.y}px`,
                width: `${geo.audio.w}px`,
                height: `${geo.audio.h}px`,
              }}
            >
              <span className="clip-tag">{currentPlan?.audio?.name || "SFX Vine Boom (A1)"}</span>
              <div className="clip-audio-waveform">
                <span style={{ height: "40%" }} />
                <span style={{ height: "70%" }} />
                <span style={{ height: "100%" }} />
                <span style={{ height: "85%" }} />
                <span style={{ height: "60%" }} />
                <span style={{ height: "90%" }} />
                <span style={{ height: "50%" }} />
                <span style={{ height: "30%" }} />
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
}
