import React, { useEffect, useRef, useState, useCallback } from "react";
import { Sparkles, Scissors, Check, Clapperboard, Trash2 } from "lucide-react";

// Generate a randomized edit plan every time Auto Edit runs
function generateRandomEditPlan(assets = []) {
  const asset0 = assets[0] || {
    id: "asset-raw-sample-01",
    name: "Camera_A_Speaker_Main.mp4",
    type: "image",
    src: "/assets/sample-portrait.png",
  };
  const asset1 = assets[1] || {
    id: "asset-raw-sample-02",
    name: "B_Roll_Studio_Setup.mp4",
    type: "image",
    src: "/assets/smart/auto-edit-card-bg.webp",
  };
  const asset2 = assets[2] || {
    id: "asset-raw-sample-03",
    name: "Zomato_UPI_Promo.png",
    type: "image",
    src: "/assets/stickers/trend-flame.png",
  };
  const asset3 = assets[3] || {
    id: "asset-raw-sample-04",
    name: "SFX_Vine_Boom.mp3",
    type: "audio",
    src: "/assets/sound-effects/bell-hit.mp3",
  };

  // 50% chance to flip which asset is placed in the first slot vs the last part of timeline
  const isAltOrder = Math.random() > 0.5;
  const primaryAsset = isAltOrder ? asset1 : asset0;
  const secondaryAsset = isAltOrder ? asset0 : asset1;
  const primaryIndex = isAltOrder ? 1 : 0;
  const secondaryIndex = isAltOrder ? 0 : 1;

  // Randomized durations
  const duration1 = Number((2.8 + Math.random() * 0.8).toFixed(2)); // 2.8s - 3.6s
  const duration2 = Number((3.6 + Math.random() * 1.0).toFixed(2)); // 3.6s - 4.6s
  const gapDuration = Number((1.6 + Math.random() * 0.6).toFixed(2)); // 1.6s - 2.2s
  const stickerStart = Number((1.2 + Math.random() * 1.6).toFixed(2));

  // Thumbnail-matched realistic matte palettes (zero bloom)
  const paletteA = ["#d59b72", "#bc7c4f", "#8b5a3c", "#3e3b38", "#e8ded1"];
  const paletteB = ["#c2653c", "#944422", "#473c35", "#d68c45", "#2a2d34"];
  const paletteZomato = ["#cb202d", "#b51c27", "#8c1d24", "#e89297", "#f3f4f6"];
  const paletteAudio = ["#587b58", "#3d5a3d", "#7a8a4b", "#c49a63", "#2c3e2c"];

  return {
    isAltOrder,
    cut1: {
      asset: primaryAsset,
      assetIndex: primaryIndex,
      start: 0,
      duration: duration1,
      name: `${primaryAsset.name} [Take ${isAltOrder ? "B" : "A"}]`,
      colorPalette: isAltOrder ? paletteB : paletteA,
    },
    cut2: {
      asset: secondaryAsset,
      assetIndex: secondaryIndex,
      start: duration1,
      duration: duration2,
      name: `${secondaryAsset.name} [Take ${isAltOrder ? "A" : "B"}]`,
      colorPalette: isAltOrder ? paletteA : paletteB,
    },
    deadAir: {
      start: duration1,
      duration: gapDuration,
    },
    sticker: {
      asset: asset2,
      assetIndex: 2,
      start: stickerStart,
      duration: 2.2,
      colorPalette: paletteZomato,
    },
    audio: {
      asset: asset3,
      assetIndex: 3,
      start: duration1 + 0.1,
      duration: 1.6,
      colorPalette: paletteAudio,
    },
    captions: [
      {
        id: `caption-1-${Date.now()}`,
        start: 0.35,
        end: duration1 - 0.15,
        text: isAltOrder
          ? "Dekho kaise editing automate hoti hai real time mein"
          : "Aaj hum baat karenge top AI tools ke baare mein",
      },
      {
        id: `caption-2-${Date.now()}`,
        start: duration1 + 0.1,
        end: duration1 + duration2 - 0.2,
        text: isAltOrder
          ? "Timeline tracks perfectly synchronize ho chuke hain"
          : "Jo aapke workflow ko 10x fast kar denge",
      },
    ],
  };
}

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
  const audioTrack = document.querySelector(".audio-track.music-track") || document.querySelector(".audio-track");

  let imgRect = { left: 260, top: window.innerHeight - 175, width: 700, height: 48 };
  if (imageTrack) {
    const r = imageTrack.getBoundingClientRect();
    if (r.width > 50 && r.height > 20) {
      imgRect = { left: r.left, top: r.top, width: r.width, height: r.height };
    }
  }

  let overlayRect = { left: imgRect.left, top: imgRect.top - 38, width: imgRect.width, height: 32 };
  if (overlayTrack) {
    const r = overlayTrack.getBoundingClientRect();
    if (r.width > 50) {
      overlayRect = { left: r.left, top: r.top, width: r.width, height: r.height };
    }
  }

  let audioRect = { left: imgRect.left, top: imgRect.top + imgRect.height + 6, width: imgRect.width, height: 32 };
  if (audioTrack) {
    const r = audioTrack.getBoundingClientRect();
    if (r.width > 50) {
      audioRect = { left: r.left, top: r.top, width: r.width, height: r.height };
    }
  }

  return {
    imageTrack: imgRect,
    overlayTrack: overlayRect,
    audioTrack: audioRect,
  };
}

// Computes the pixel geometry of all clips directly on the real track lines
function computeClipGeometry(plan, layout) {
  const img = layout.imageTrack;
  const overlay = layout.overlayTrack;
  const audio = layout.audioTrack;

  // Use visible track area so clips physically fit the visible timeline viewport
  const viewportW = Math.max(400, Math.min(img.width, window.innerWidth - img.left - 48));
  const totalDuration = (plan.cut1.duration || 3.15) + (plan.cut2.duration || 4.2);
  const gapW = 80;
  const usableW = Math.min(viewportW - gapW, 600);

  const cut1W = Math.max(170, Math.round((plan.cut1.duration / totalDuration) * usableW));
  const cut2W = Math.max(190, usableW - cut1W);

  const cut1X = img.left;
  const cut1Y = img.top;
  const cut1H = img.height;

  const deadAirX = cut1X + cut1W;
  const deadAirY = cut1Y;
  const deadAirW = gapW;
  const deadAirH = cut1H;

  // Cut 2 sits in the LAST part of the timeline before ripple
  const cut2PreX = deadAirX + deadAirW;
  const cut2PostX = cut1X + cut1W;
  const cut2Y = cut1Y;
  const cut2H = cut1H;

  // Overlay sticker on real overlay track
  const overlayX = img.left + Math.round(cut1W * 0.45);
  const overlayY = overlay.top;
  const overlayW = 145;
  const overlayH = overlay.height || 34;

  // SFX Audio on real audio track
  const audioX = img.left + cut1W + 10;
  const audioY = audio.top;
  const audioW = 135;
  const audioH = audio.height || 32;

  return {
    cut1: { x: cut1X, y: cut1Y, w: cut1W, h: cut1H },
    deadAir: { x: deadAirX, y: deadAirY, w: deadAirW, h: deadAirH },
    cut2Pre: { x: cut2PreX, y: cut2Y, w: cut2W, h: cut2H },
    cut2Post: { x: cut2PostX, y: cut2Y, w: cut2W, h: cut2H },
    overlay: { x: overlayX, y: overlayY, w: overlayW, h: overlayH },
    audio: { x: audioX, y: audioY, w: audioW, h: audioH },
  };
}

export function AutoEditEngine({
  running = false,
  sessionId = 0,
  hasExistingTimeline = false,
  userAssets = [],
  onResetTimeline,
  onComplete,
  onCommitTimeline,
  t = (k, fallback) => fallback || k,
}) {
  const canvasRef = useRef(null);
  const animationFrameRef = useRef(null);
  const particlesRef = useRef([]);

  const isExecutingRef = useRef(false);
  const onResetTimelineRef = useRef(onResetTimeline);
  const onCommitTimelineRef = useRef(onCommitTimeline);
  const onCompleteRef = useRef(onComplete);
  const hasExistingTimelineRef = useRef(hasExistingTimeline);

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

  // Phases: "idle" | "timeline-collapse" | "wave" | "collapse-1" | "collapse-2" | "splicing" | "collapse-3-4" | "processing" | "done"
  const [phase, setPhase] = useState("idle");
  const [statusText, setStatusText] = useState("");
  const [processingPercent, setProcessingPercent] = useState(0);

  // Active plan & computed clip geometry for current run
  const [currentPlan, setCurrentPlan] = useState(null);
  const [clipGeometry, setClipGeometry] = useState(null);

  // Active Presence on Timeline Track: "none" | "cut1" | "cut2" | "overlay-audio"
  const [currentPresence, setCurrentPresence] = useState("none");

  // Timeline Track Live Visual State (Matte, non-blooming)
  const [timelineTracks, setTimelineTracks] = useState({
    cut1Merged: false,
    cut2Merged: false,
    silenceDetected: false,
    isSplicing: false,
    gapClosed: false,
    overlayMerged: false,
    audioMerged: false,
  });

  // 60FPS Minimal Pixel Canvas Loop (ZERO BLOOM, tiny minimal grains)
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

      // Disable bloom and blur completely
      ctx.shadowBlur = 0;
      ctx.shadowColor = "transparent";

      const particles = particlesRef.current;
      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];

        if (p.delay > 0) {
          p.delay -= 1;
          continue;
        }

        // Dissolution / collapse particle mode (for timeline clean slate wipe)
        if (p.isCollapsing) {
          p.x += p.vx;
          p.y += p.vy;
          p.alpha -= 0.04;
          if (p.alpha <= 0) {
            particles.splice(i, 1);
            continue;
          }
          ctx.fillStyle = p.color;
          ctx.globalAlpha = Math.max(0, p.alpha);
          ctx.fillRect(p.x, p.y, p.size, p.size);
          continue;
        }

        p.progress += p.speed;

        // When particle arrives at destination:
        // 1. COMBINES IN THE EXACT RECTANGULAR SHAPE OF THE TIMELINE CLIP
        // 2. HOLDS THE CLIP SHAPE DIRECTLY ON THE TRACK
        // 3. DISAPPEARS (fades out smoothly as the solid clip takes over)
        if (p.progress >= 1) {
          p.linger -= 1;
          if (p.linger <= 0) {
            particles.splice(i, 1);
            continue;
          }

          // Trigger solid clip reveal precisely as particles start disappearing
          if (p.linger === 14 && !p.hasTriggeredMerge && p.onMerged) {
            p.hasTriggeredMerge = true;
            p.onMerged();
          }

          // Full opacity while forming shape (> 15), then disappears (<= 15)
          let alpha = 1.0;
          if (p.linger <= 15) {
            alpha = Math.max(0, p.linger / 15);
          }

          ctx.fillStyle = p.color;
          ctx.globalAlpha = alpha;
          // Render at its exact coordinate in the rectangular clip shape
          ctx.fillRect(p.targetX, p.targetY, p.size, p.size);
          continue;
        }

        const prog = p.progress;

        // Curved aerodynamic trajectory from Media Pool thumbnail to specific timeline area
        const bx =
          (1 - prog) * (1 - prog) * p.startX +
          2 * (1 - prog) * prog * p.cpX +
          prog * prog * p.targetX;
        const by =
          (1 - prog) * (1 - prog) * p.startY +
          2 * (1 - prog) * prog * p.cpY +
          prog * prog * p.targetY;

        // Subtle micro-turbulence during flight
        const turbulence = Math.sin(prog * 8 + p.seed) * (1 - prog) * 5;
        p.x = bx + turbulence;
        p.y = by + turbulence * 0.3;

        // Sharp minimal opacity
        p.alpha = prog < 0.1 ? prog / 0.1 : 1;

        ctx.fillStyle = p.color;
        ctx.globalAlpha = Math.max(0, Math.min(1, p.alpha));

        // Draw crisp minimal micro-pixel (no blurry circles or bloom halos)
        ctx.fillRect(p.x, p.y, p.size, p.size);
      }

      animationFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener("resize", resize);
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    };
  }, []);

  // Collapse specific Media Pool thumbnail and stream particles directly to its exact track coordinates
  const collapseAndStreamToTimeline = useCallback((asset, assetIndex, targetConfig) => {
    return new Promise((resolve) => {
      // 1. Locate specific thumbnail in Media Pool DOM
      let sourceLeft = 140;
      let sourceTop = 200 + assetIndex * 48;
      let sourceWidth = 140;
      let sourceHeight = 40;

      let targetEl = null;
      if (asset?.id) {
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

        // Thumbnail collapses directly in the Media Pool
        targetEl.classList.add("is-collapsing-thumbnail");
      }

      // 2. Timeline destination coordinates (Directly on real track!)
      const targetX = targetConfig.x;
      const targetY = targetConfig.y;
      const targetW = targetConfig.w;
      const targetH = targetConfig.h;

      // Calculate trajectory apex across canvas
      const cpX = (sourceLeft + targetX) / 2 + (Math.random() - 0.5) * 30;
      const cpY = Math.min(sourceTop, targetY) - 95;

      const colors = targetConfig.colors || ["#d59b72", "#bc7c4f", "#8b5a3c", "#3e3b38"];

      // 200 minimal micro-particles mapped into the exact rectangular shape of the timeline clip
      const particleCount = 200;
      const shapePoints = generateClipShapePoints(targetX, targetY, targetW, targetH, particleCount);

      for (let i = 0; i < particleCount; i++) {
        // Origin: distributed across thumbnail surface
        const startX = sourceLeft + Math.random() * sourceWidth;
        const startY = sourceTop + Math.random() * sourceHeight;

        // Destination: exact assigned point in the rectangular clip shape
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
          size: 1.0 + Math.random() * 0.8, // 1.0px - 1.8px (minimal, not tacky)
          alpha: 0,
          progress: 0,
          speed: 0.022 + Math.random() * 0.014,
          delay: Math.random() * 12,
          linger: 42, // Holds shape for ~28 frames, then disappears over 14 frames
          hasTriggeredMerge: false,
          onMerged: targetConfig.onMerged,
        });
      }

      // Resolve once particles have assembled in shape and disappeared
      setTimeout(() => {
        resolve();
      }, 1120);
    });
  }, []);

  // Main Orchestration Sequence — Re-runs & randomizes whenever running becomes true or sessionId changes
  useEffect(() => {
    if (!running) {
      isExecutingRef.current = false;
      setPhase("idle");
      setProcessingPercent(0);
      setCurrentPresence("none");
      setClipGeometry(null);
      setTimelineTracks({
        cut1Merged: false,
        cut2Merged: false,
        silenceDetected: false,
        isSplicing: false,
        gapClosed: false,
        overlayMerged: false,
        audioMerged: false,
      });

      // Reset collapsed thumbnails in Media Pool
      document.querySelectorAll(".asset-row-wrap.is-collapsing-thumbnail").forEach((el) => {
        el.classList.remove("is-collapsing-thumbnail");
      });
      document.body.classList.remove("is-timeline-collapsing");
      return;
    }

    if (isExecutingRef.current) return;
    isExecutingRef.current = true;

    let isCancelled = false;

    const executeRandomizedAutoEdit = async () => {
      // 0. CLEAN SLATE CHECK: If previous timeline exists, collapse it entirely first!
      if (hasExistingTimelineRef.current) {
        setPhase("timeline-collapse");
        setStatusText("Collapsing existing timeline — Clearing slate for fresh edit...");
        document.body.classList.add("is-timeline-collapsing");

        // Spawn dissolving implosion particles from existing timeline clips
        const existingClips = document.querySelectorAll(".merged-track-clip, .timeline-board .image-clip, .silence-dead-air-gap");
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

        // Wipe React timeline state to pristine empty clean slate
        if (onResetTimelineRef.current) {
          onResetTimelineRef.current();
        }

        // Reset HUD tracks
        setTimelineTracks({
          cut1Merged: false,
          cut2Merged: false,
          silenceDetected: false,
          isSplicing: false,
          gapClosed: false,
          overlayMerged: false,
          audioMerged: false,
        });

        // Reset any collapsed thumbnails in Media Pool so they are full again
        document.querySelectorAll(".asset-row-wrap.is-collapsing-thumbnail").forEach((el) => {
          el.classList.remove("is-collapsing-thumbnail");
        });

        document.body.classList.remove("is-timeline-collapsing");
        await sleep(200);
        if (isCancelled) return;
      }

      // 1. Generate fresh randomized edit plan
      const plan = generateRandomEditPlan(userAssets);
      setCurrentPlan(plan);

      // 2. Compute exact 1:1 pixel coordinates directly on the real timeline tracks
      const layout = getTimelineLayout();
      const geo = computeClipGeometry(plan, layout);
      setClipGeometry(geo);

      // 3. WAVE SWEEP: Single-shot upward wave (0s - 1.0s, matte, zero bloom)
      setPhase("wave");
      setStatusText("Acoustic analysis: Waveform frequency sweep...");
      await sleep(950);
      if (isCancelled) return;

      // 4. FIRST CLIP: Spatial Presence illuminated on real .image-track -> Thumbnail collapses -> Particles traverse -> Combine in shape -> Disappear
      setPhase("collapse-1");
      setCurrentPresence("cut1");
      setStatusText(`Target Presence: ${plan.cut1.asset.name} · Assembling Cut 01 on Visuals track (0.00s)...`);
      await collapseAndStreamToTimeline(plan.cut1.asset, plan.cut1.assetIndex, {
        x: geo.cut1.x,
        y: geo.cut1.y,
        w: geo.cut1.w,
        h: geo.cut1.h,
        colors: plan.cut1.colorPalette,
        onMerged: () => {
          setTimelineTracks((prev) => ({ ...prev, cut1Merged: true }));
          setCurrentPresence("none");
        },
      });
      if (isCancelled) return;
      await sleep(260);

      // 5. SECOND CLIP: Asset sits in last part of real .image-track -> Particles traverse all the way across canvas -> Combine in shape -> Disappear
      setPhase("collapse-2");
      setCurrentPresence("cut2");
      setStatusText(`Target Presence: ${plan.cut2.asset.name} · Streaming across to Cut 02 in last part of track...`);
      await collapseAndStreamToTimeline(plan.cut2.asset, plan.cut2.assetIndex, {
        x: geo.cut2Pre.x,
        y: geo.cut2Pre.y,
        w: geo.cut2Pre.w,
        h: geo.cut2Pre.h,
        colors: plan.cut2.colorPalette,
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
      await sleep(320);

      // 6. DYNAMIC SPLICING ANIMATION: Laser blade drops right at cut point on the track, gap closes, Cut 2 ripples left
      setPhase("splicing");
      setStatusText(`Laser blade splicing dead-air silence at ${plan.cut1.duration}s...`);
      setTimelineTracks((prev) => ({ ...prev, isSplicing: true }));
      await sleep(550);
      if (isCancelled) return;

      // Magnetic ripple closure directly on track
      setStatusText("Magnetic ripple snap: Sealing gap and joining video cuts...");
      setTimelineTracks((prev) => ({ ...prev, gapClosed: true, isSplicing: false }));
      await sleep(750);
      if (isCancelled) return;

      // 7. STICKER & AUDIO: Presence illuminated on Overlay & Audio tracks -> Traverse -> Combine in shape -> Disappear -> Solidify
      setPhase("collapse-3-4");
      setCurrentPresence("overlay-audio");
      setStatusText("Target Presence: Overlay sticker & SFX audio — Assembling tracks...");
      await collapseAndStreamToTimeline(plan.sticker.asset, plan.sticker.assetIndex, {
        x: geo.overlay.x,
        y: geo.overlay.y,
        w: geo.overlay.w,
        h: geo.overlay.h,
        colors: plan.sticker.colorPalette,
        onMerged: () => {
          setTimelineTracks((prev) => ({ ...prev, overlayMerged: true }));
        },
      });
      if (isCancelled) return;

      await collapseAndStreamToTimeline(plan.audio.asset, plan.audio.assetIndex, {
        x: geo.audio.x,
        y: geo.audio.y,
        w: geo.audio.w,
        h: geo.audio.h,
        colors: plan.audio.colorPalette,
        onMerged: () => {
          setTimelineTracks((prev) => ({ ...prev, audioMerged: true }));
          setCurrentPresence("none");
        },
      });
      if (isCancelled) return;
      await sleep(450);

      // 8. CINEMA PROCESSING SCREEN (Matte, non-blooming clapperboard -> cinema reel)
      setPhase("processing");
      setStatusText("Compiling master timeline & rendering preview...");

      for (let p = 15; p <= 100; p += 6) {
        setProcessingPercent(p);
        await sleep(85);
        if (isCancelled) return;
      }
      await sleep(300);
      if (isCancelled) return;

      // 9. DONE: Commit randomized plan to Timeline Studio & start live video preview
      setPhase("done");
      setStatusText("Timeline assembled! Commencing preview playback...");

      if (onCommitTimelineRef.current) {
        onCommitTimelineRef.current(plan);
      }

      await sleep(400);
      if (isCancelled) return;

      setPhase("idle");
      isExecutingRef.current = false;
      if (onCompleteRef.current) {
        onCompleteRef.current();
      }
    };

    executeRandomizedAutoEdit();

    return () => {
      isCancelled = true;
    };
  }, [running, sessionId, userAssets, collapseAndStreamToTimeline]);

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  const geo = clipGeometry;

  return (
    <>
      {/* 2D Canvas for micro-particles (ZERO BLOOM, always in DOM) */}
      <canvas
        ref={canvasRef}
        className="particle-flight-canvas"
        style={{
          display: phase === "idle" && !running ? "none" : "block",
        }}
      />

      {/* PHASE: Timeline Collapse Alert */}
      {phase === "timeline-collapse" && (
        <div className="timeline-collapse-banner">
          <Trash2 size={13} strokeWidth={1.5} />
          <span>Collapsing previous timeline — Clearing slate...</span>
        </div>
      )}

      {/* PHASE 1: Transparent Sound Waves Moving from Bottom to Top (MATTE, ZERO BLOOM) */}
      {phase === "wave" && (
        <div className="soundwave-sweep-container">
          <div className="soundwave-band">
            <svg
              className="soundwave-svg"
              viewBox="0 0 1440 220"
              preserveAspectRatio="none"
            >
              <path
                className="soundwave-line primary"
                d="M 0,110 C 120,40 240,180 360,110 C 480,30 600,190 720,110 C 840,30 960,180 1080,110 C 1200,40 1320,170 1440,110"
              />
              <path
                className="soundwave-line secondary"
                d="M 0,110 C 150,170 300,50 450,110 C 600,180 750,40 900,110 C 1050,180 1200,40 1350,110 C 1400,140 1440,110 1440,110"
              />
            </svg>
            <div className="soundwave-bars-row">
              {Array.from({ length: 48 }).map((_, i) => (
                <span key={i} className="soundwave-bar" />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* DYNAMIC TIMELINE ASSEMBLY VIEWPORT LAYER — 100% MATCHED TO REAL TRACK POSITIONS */}
      {geo && phase !== "processing" && phase !== "idle" && (
        <div className="timeline-assembly-viewport-layer">
          {/* Cut 1 Target Presence Slot (Directly on real .image-track!) */}
          {currentPresence === "cut1" && !timelineTracks.cut1Merged && (
            <div
              className="timeline-presence-slot"
              style={{
                position: "fixed",
                left: `${geo.cut1.x}px`,
                top: `${geo.cut1.y}px`,
                width: `${geo.cut1.w}px`,
                height: `${geo.cut1.h}px`,
              }}
            >
              <span className="presence-corner top-left" />
              <span className="presence-corner top-right" />
              <span className="presence-corner bottom-left" />
              <span className="presence-corner bottom-right" />
              <span className="presence-label">TARGET PRESENCE · CUT 01</span>
              <span className="presence-time">0.00s — {currentPlan?.cut1?.duration || "3.15"}s</span>
            </div>
          )}

          {/* Cut 1 Merged Clip (Directly on real .image-track!) */}
          {timelineTracks.cut1Merged && (
            <div
              className="merged-track-clip clip-take-1"
              style={{
                position: "fixed",
                left: `${geo.cut1.x}px`,
                top: `${geo.cut1.y}px`,
                width: `${geo.cut1.w}px`,
                height: `${geo.cut1.h}px`,
              }}
            >
              <span className="clip-tag">{currentPlan?.cut1?.name || "Visual Cut 01"}</span>
              <span className="clip-time">0.00s — {currentPlan?.cut1?.duration || "3.15"}s</span>
            </div>
          )}

          {/* Silence Dead-Air Gap (Between Cut 1 and Cut 2 on real .image-track!) */}
          {timelineTracks.silenceDetected && (
            <div
              className={`silence-dead-air-gap ${timelineTracks.gapClosed ? "is-gap-eliminated" : ""}`}
              style={{
                position: "fixed",
                left: `${geo.deadAir.x}px`,
                top: `${geo.deadAir.y}px`,
                width: `${timelineTracks.gapClosed ? 0 : geo.deadAir.w}px`,
                height: `${geo.deadAir.h}px`,
              }}
            >
              {!timelineTracks.gapClosed && (
                <span className="dead-air-label">DEAD AIR {currentPlan?.deadAir?.duration || "2.25"}s</span>
              )}
            </div>
          )}

          {/* Cut 2 Target Presence Slot (In the LAST part of real .image-track!) */}
          {currentPresence === "cut2" && !timelineTracks.cut2Merged && (
            <div
              className="timeline-presence-slot"
              style={{
                position: "fixed",
                left: `${geo.cut2Pre.x}px`,
                top: `${geo.cut2Pre.y}px`,
                width: `${geo.cut2Pre.w}px`,
                height: `${geo.cut2Pre.h}px`,
              }}
            >
              <span className="presence-corner top-left" />
              <span className="presence-corner top-right" />
              <span className="presence-corner bottom-left" />
              <span className="presence-corner bottom-right" />
              <span className="presence-label">TARGET PRESENCE · CUT 02 (LAST PART)</span>
              <span className="presence-time">
                {currentPlan?.cut1?.duration || "3.15"}s — {(Number(currentPlan?.cut1?.duration || 3.15) + Number(currentPlan?.cut2?.duration || 4.2)).toFixed(2)}s
              </span>
            </div>
          )}

          {/* Cut 2 Merged Clip (Slides left smoothly on magnetic ripple!) */}
          {timelineTracks.cut2Merged && (
            <div
              className="merged-track-clip clip-take-2"
              style={{
                position: "fixed",
                left: `${timelineTracks.gapClosed ? geo.cut2Post.x : geo.cut2Pre.x}px`,
                top: `${geo.cut2Pre.y}px`,
                width: `${geo.cut2Pre.w}px`,
                height: `${geo.cut2Pre.h}px`,
                transition: "left 0.45s cubic-bezier(0.85, 0, 0.15, 1)",
              }}
            >
              <span className="clip-tag">{currentPlan?.cut2?.name || "Visual Cut 02"}</span>
              <span className="clip-time">
                {currentPlan?.cut1?.duration || "3.15"}s — {(Number(currentPlan?.cut1?.duration || 3.15) + Number(currentPlan?.cut2?.duration || 4.2)).toFixed(2)}s
              </span>
            </div>
          )}

          {/* Laser Splicer Blade (Directly on real track at the cut point!) */}
          {timelineTracks.isSplicing && !timelineTracks.gapClosed && (
            <div
              className="dynamic-splicer-laser-line"
              style={{
                position: "fixed",
                left: `${geo.deadAir.x}px`,
                top: `${geo.deadAir.y - 8}px`,
                height: `${geo.deadAir.h + 16}px`,
              }}
            >
              <div className="laser-beam" />
              <div className="laser-sparks" />
            </div>
          )}

          {/* Overlay Sticker Presence & Merged Clip (Directly on real Overlay track!) */}
          {currentPresence === "overlay-audio" && !timelineTracks.overlayMerged && (
            <div
              className="timeline-presence-slot"
              style={{
                position: "fixed",
                left: `${geo.overlay.x}px`,
                top: `${geo.overlay.y}px`,
                width: `${geo.overlay.w}px`,
                height: `${geo.overlay.h}px`,
              }}
            >
              <span className="presence-label">PRESENCE · ZOMATO PiP</span>
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
              <span className="clip-tag">Zomato Promo (PiP)</span>
            </div>
          )}

          {/* Audio Boom Presence & Merged Clip (Directly on real Audio track!) */}
          {currentPresence === "overlay-audio" && !timelineTracks.audioMerged && (
            <div
              className="timeline-presence-slot"
              style={{
                position: "fixed",
                left: `${geo.audio.x}px`,
                top: `${geo.audio.y}px`,
                width: `${geo.audio.w}px`,
                height: `${geo.audio.h}px`,
              }}
            >
              <span className="presence-label">PRESENCE · SFX BOOM</span>
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
              <span className="clip-tag">SFX Vine Boom (A1)</span>
            </div>
          )}
        </div>
      )}

      {/* PHASE 8: Cinema Processing Loading Screen (MATTE, ZERO BLOOM) */}
      {phase === "processing" && (
        <div className="cinema-morph-overlay">
          <div className="cinema-morph-card">
            {/* Clapperboard to Cinema Reel Morph Graphic */}
            <div className="cinema-morph-stage">
              <div className="clapperboard-morph-container">
                <div className="clapper-stick top-stick" />
                <div className="clapper-stick bottom-stick" />
                <div className="clapper-slate-body">
                  <div className="slate-label">SCENE 01 · TAKE {currentPlan?.isAltOrder ? "02" : "01"}</div>
                  <div className="slate-title">INDIC AUTO-CUT</div>
                </div>
              </div>

              <div className="cinema-reel-container">
                <div className="cinema-reel-disk">
                  <div className="reel-hole hole-1" />
                  <div className="reel-hole hole-2" />
                  <div className="reel-hole hole-3" />
                  <div className="reel-hole hole-4" />
                  <div className="reel-hole hole-5" />
                  <div className="reel-hole hole-6" />
                  <div className="reel-center-spindle" />
                </div>
                <div className="cinema-film-ribbon" />
              </div>
            </div>

            {/* Processing HUD & Progress */}
            <div className="cinema-processing-info">
              <div className="cinema-processing-title-row">
                <Clapperboard size={15} strokeWidth={1.5} className="cinema-clapper-icon" />
                <span className="cinema-processing-title">Compiling Master Timeline</span>
                <span className="cinema-processing-percent">{processingPercent}%</span>
              </div>

              <div className="cinema-progress-track">
                <div
                  className="cinema-progress-fill"
                  style={{ width: `${processingPercent}%` }}
                />
              </div>

              <div className="cinema-processing-subtext">
                {processingPercent < 45
                  ? "Splicing dead-air & synchronizing Romanized captions..."
                  : processingPercent < 85
                  ? "Synthesizing dynamic sticker overlays & meme SFX audio..."
                  : "Finalizing WebCodecs preview & shifting to timeline..."}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Floating Status Pill (Matte, non-blooming) */}
      {statusText && phase !== "processing" && phase !== "idle" && (
        <div className="assembly-status-pill">
          <div className="assembly-pulse-icon">
            {phase === "done" ? (
              <Check size={14} strokeWidth={2} />
            ) : phase === "splicing" ? (
              <Scissors size={14} strokeWidth={1.5} />
            ) : (
              <Sparkles size={14} strokeWidth={1.5} />
            )}
          </div>
          <span>{statusText}</span>
        </div>
      )}
    </>
  );
}
