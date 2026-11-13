import React, { useEffect, useRef, useState, useCallback } from "react";
import { Sparkles, Scissors, Check, Clapperboard, Video, Image as ImageIcon, Music } from "lucide-react";

export function AutoEditEngine({
  running = false,
  onComplete,
  onCommitTimeline,
  t = (k, fallback) => fallback || k,
}) {
  const canvasRef = useRef(null);
  const animationFrameRef = useRef(null);
  const trailingSparksRef = useRef([]);

  const isExecutingRef = useRef(false);
  const onCommitTimelineRef = useRef(onCommitTimeline);
  const onCompleteRef = useRef(onComplete);

  useEffect(() => {
    onCommitTimelineRef.current = onCommitTimeline;
  }, [onCommitTimeline]);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  // Phases: "idle" | "wave" | "flight-1" | "flight-2" | "splicing" | "flight-3-4" | "processing" | "done"
  const [phase, setPhase] = useState("idle");
  const [statusText, setStatusText] = useState("");
  const [processingPercent, setProcessingPercent] = useState(0);

  // Active Deforming Flying Card State
  const [activeFlight, setActiveFlight] = useState(null);

  // Timeline Assembly Live Visuals State
  const [timelineClips, setTimelineClips] = useState({
    clip1: false,
    clip2: false,
    gapClosed: false,
    isSplicing: false,
    overlay: false,
    audio: false,
    captions: false,
  });

  // Canvas 2D Loop for refined trailing embers (12-16 subtle sparks per flight, NOT 400 dots)
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

      const sparks = trailingSparksRef.current;
      for (let i = sparks.length - 1; i >= 0; i--) {
        const s = sparks[i];
        s.progress += s.speed;

        if (s.progress >= 1) {
          sparks.splice(i, 1);
          continue;
        }

        s.x += s.vx;
        s.y += s.vy;
        s.alpha = Math.max(0, 1 - s.progress);

        ctx.save();
        ctx.globalAlpha = s.alpha;
        ctx.fillStyle = s.color;
        ctx.shadowColor = s.color;
        ctx.shadowBlur = 8;

        ctx.beginPath();
        ctx.arc(s.x, s.y, s.size * (1 - s.progress * 0.5), 0, Math.PI * 2);
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

  // Deform and fly a specific media asset from Media Pool to the Timeline track
  const animateDeformingFlight = useCallback((assetIndex, targetConfig) => {
    return new Promise((resolve) => {
      // 1. Locate specific asset row in Media Pool
      const assetRows = document.querySelectorAll(".asset-row-wrap");
      const targetAssetEl =
        assetRows[assetIndex] ||
        assetRows[0] ||
        document.querySelector(".media-panel") ||
        document.querySelector(".drop-zone");

      let startX = 160;
      let startY = 190 + assetIndex * 50;
      let startW = 180;
      let startH = 46;

      if (targetAssetEl) {
        const rect = targetAssetEl.getBoundingClientRect();
        startX = rect.left;
        startY = rect.top;
        startW = Math.max(rect.width, 140);
        startH = Math.max(rect.height, 40);
        targetAssetEl.classList.add("is-peeling-active");
      }

      // 2. Timeline target coordinates
      const targetX = targetConfig.x;
      const targetY = targetConfig.y;
      const targetW = targetConfig.w || 160;
      const targetH = targetConfig.h || 42;

      // Curved control point arching over the central canvas
      const cpX = (startX + targetX) / 2 + (Math.random() - 0.5) * 80;
      const cpY = Math.min(startY, targetY) - 100;

      const duration = 900; // ms flight duration
      const startTime = performance.now();

      const updateFlight = (now) => {
        const elapsed = now - startTime;
        const rawT = Math.min(1, elapsed / duration);
        // Smooth easeInOutCubic
        const t =
          rawT < 0.5
            ? 4 * rawT * rawT * rawT
            : 1 - Math.pow(-2 * rawT + 2, 3) / 2;

        // Quadratic bezier trajectory
        const curX =
          (1 - t) * (1 - t) * startX +
          2 * (1 - t) * t * cpX +
          t * t * targetX;
        const curY =
          (1 - t) * (1 - t) * startY +
          2 * (1 - t) * t * cpY +
          t * t * targetY;

        // Elastic shape deformation: stretches along velocity vector
        const curW = (1 - t) * startW + t * targetW;
        const curH = (1 - t) * startH + t * targetH;

        // Velocity-based dynamic shear & stretch
        const stretchX = 1 + Math.sin(t * Math.PI) * 0.18;
        const stretchY = 1 - Math.sin(t * Math.PI) * 0.12;
        const tiltDeg = (1 - t) * -6 + t * 4;

        // Emit subtle trailing embers (only 2 sparks every few frames)
        if (Math.random() < 0.6) {
          trailingSparksRef.current.push({
            x: curX + curW / 2 + (Math.random() - 0.5) * 16,
            y: curY + curH / 2 + (Math.random() - 0.5) * 12,
            vx: (Math.random() - 0.5) * 1.5,
            vy: (Math.random() - 0.5) * 1.5,
            size: 2 + Math.random() * 3,
            color: targetConfig.color || "#e05638",
            progress: 0,
            speed: 0.04 + Math.random() * 0.03,
            alpha: 1,
          });
        }

        setActiveFlight({
          name: targetConfig.name,
          type: targetConfig.type,
          color: targetConfig.color || "#e05638",
          x: curX,
          y: curY,
          w: curW,
          h: curH,
          scaleX: stretchX,
          scaleY: stretchY,
          rotate: tiltDeg,
          progress: t,
        });

        if (rawT < 1) {
          requestAnimationFrame(updateFlight);
        } else {
          setActiveFlight(null);
          if (targetAssetEl) {
            targetAssetEl.classList.remove("is-peeling-active");
          }
          resolve();
        }
      };

      requestAnimationFrame(updateFlight);
    });
  }, []);

  // Main Orchestration Sequence — Single-shot per trigger
  useEffect(() => {
    if (!running) {
      isExecutingRef.current = false;
      setPhase("idle");
      setActiveFlight(null);
      setProcessingPercent(0);
      setTimelineClips({
        clip1: false,
        clip2: false,
        gapClosed: false,
        isSplicing: false,
        overlay: false,
        audio: false,
        captions: false,
      });
      return;
    }

    if (isExecutingRef.current) return;
    isExecutingRef.current = true;

    let isCancelled = false;

    const executeDeformationAssembly = async () => {
      // 1. WAVE SWEEP: Single-shot upward wave (0s - 1.0s)
      setPhase("wave");
      setStatusText("Acoustic frequency analysis: Single bottom-to-top sweep...");
      await sleep(1050);
      if (isCancelled) return;

      // Determine timeline target lane position
      const timelineEl =
        document.querySelector(".timeline-track-content") ||
        document.querySelector(".timeline-track-lane") ||
        document.querySelector(".timeline-scroll") ||
        document.querySelector(".timeline");

      let baseX = window.innerWidth * 0.36;
      let baseY = window.innerHeight - 170;

      if (timelineEl) {
        const rect = timelineEl.getBoundingClientRect();
        baseX = rect.left + 50;
        baseY = rect.top + 38;
      }

      // 2. ASSET 1 (Camera A): Deforms and flies to Timeline Visuals (Take 1)
      setPhase("flight-1");
      setStatusText("Deforming Camera A footage — Snapping to Timeline Visuals (0.00s)...");
      await animateDeformingFlight(0, {
        name: "Camera_A_Speaker.mp4",
        type: "video",
        color: "#e05638",
        x: baseX + 20,
        y: baseY,
        w: 170,
        h: 44,
      });
      if (isCancelled) return;
      setTimelineClips((prev) => ({ ...prev, clip1: true }));
      await sleep(350);

      // 3. ASSET 2 (B-Roll Setup): Deforms and flies to Timeline Visuals (Take 2)
      setPhase("flight-2");
      setStatusText("Deforming B-Roll footage — Snapping to Timeline Visuals (Cutaway)...");
      await animateDeformingFlight(1, {
        name: "B_Roll_Studio_Setup.mp4",
        type: "video",
        color: "#ff7a00",
        x: baseX + 320,
        y: baseY,
        w: 190,
        h: 44,
      });
      if (isCancelled) return;
      setTimelineClips((prev) => ({ ...prev, clip2: true }));
      await sleep(400);

      // 4. DYNAMIC SPLICING ANIMATION: Laser blade drops, spark burst, gap eliminates & ripple cut
      setPhase("splicing");
      setStatusText("Laser blade splicing dead-air [3.15s - 5.40s] & magnetic ripple cut...");
      setTimelineClips((prev) => ({ ...prev, isSplicing: true }));
      await sleep(600);
      if (isCancelled) return;

      // Magnetic ripple closes the gap
      setTimelineClips((prev) => ({ ...prev, gapClosed: true }));
      await sleep(850);
      if (isCancelled) return;

      // 5. ASSET 3 & 4: Deform & Fly to Overlay and Audio Tracks + Captions
      setPhase("flight-3-4");
      setStatusText("Deforming Zomato promo & SFX boom — Locking into Overlay & Audio tracks...");
      await animateDeformingFlight(2, {
        name: "Zomato_UPI_Promo.png",
        type: "image",
        color: "#ffd54f",
        x: baseX + 90,
        y: baseY - 42,
        w: 150,
        h: 36,
      });
      if (isCancelled) return;
      setTimelineClips((prev) => ({ ...prev, overlay: true }));

      await animateDeformingFlight(3, {
        name: "SFX_Vine_Boom.mp3",
        type: "audio",
        color: "#22c55e",
        x: baseX + 130,
        y: baseY + 48,
        w: 130,
        h: 34,
      });
      if (isCancelled) return;
      setTimelineClips((prev) => ({ ...prev, audio: true, captions: true }));
      await sleep(650);

      // 6. PROCESSING LOADING SCREEN: Clapperboard morphing into Cinema Reel
      setPhase("processing");
      setStatusText("Compiling master timeline & rendering preview...");

      for (let p = 15; p <= 100; p += 6) {
        setProcessingPercent(p);
        await sleep(95);
        if (isCancelled) return;
      }
      await sleep(350);
      if (isCancelled) return;

      // 7. DONE: Commit all tracks & preview video on timeline
      setPhase("done");
      setStatusText("Timeline assembled! Commencing preview playback...");

      if (onCommitTimelineRef.current) {
        onCommitTimelineRef.current();
      }

      await sleep(450);
      if (isCancelled) return;

      setPhase("idle");
      isExecutingRef.current = false;
      if (onCompleteRef.current) {
        onCompleteRef.current();
      }
    };

    executeDeformationAssembly();

    return () => {
      isCancelled = true;
    };
  }, [running, animateDeformingFlight]);

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  return (
    <>
      {/* 2D Canvas for subtle trailing embers (ALWAYS in DOM) */}
      <canvas
        ref={canvasRef}
        className="particle-flight-canvas"
        style={{
          display: phase === "idle" && !running ? "none" : "block",
        }}
      />

      {/* PHASE 1: Transparent Sound Waves Moving from Bottom to Top (SINGLE-SHOT) */}
      {phase === "wave" && (
        <div className="soundwave-sweep-container">
          <div className="soundwave-band">
            <div className="soundwave-glow-field" />
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
              {Array.from({ length: 54 }).map((_, i) => (
                <span
                  key={i}
                  className="soundwave-bar"
                  style={{
                    animationDelay: `${(i % 10) * 0.04}s`,
                    animationDuration: `${0.32 + (i % 6) * 0.07}s`,
                  }}
                />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ACTIVE DEFORMING FLYING ASSET CARD */}
      {activeFlight && (
        <div
          className="deforming-flight-card"
          style={{
            transform: `translate3d(${activeFlight.x}px, ${activeFlight.y}px, 0) scale(${activeFlight.scaleX}, ${activeFlight.scaleY}) rotate(${activeFlight.rotate}deg)`,
            width: `${activeFlight.w}px`,
            height: `${activeFlight.h}px`,
            "--card-accent": activeFlight.color,
            "--card-glow": `${activeFlight.color}88`,
          }}
        >
          <div className="flight-card-icon-pill">
            {activeFlight.type === "video" ? (
              <Video size={13} strokeWidth={1.5} />
            ) : activeFlight.type === "image" ? (
              <ImageIcon size={13} strokeWidth={1.5} />
            ) : (
              <Music size={13} strokeWidth={1.5} />
            )}
          </div>
          <span className="flight-card-label">{activeFlight.name}</span>
          <div className="flight-card-trail-glow" />
        </div>
      )}

      {/* DYNAMIC TIMELINE HUD OVERLAY SHOWING REAL-TIME ASSEMBLY & SPLICING */}
      {(timelineClips.clip1 || timelineClips.clip2 || phase === "splicing") && phase !== "processing" && (
        <div className="timeline-dynamic-assembly-overlay">
          {/* Visuals Lane */}
          <div className="dynamic-assembly-track visuals-track">
            {timelineClips.clip1 && (
              <div className="assembled-clip clip-take-1">
                <span className="clip-tag">Visual Cut 01</span>
                <span className="clip-time">0.00s - 3.15s</span>
              </div>
            )}

            {/* Silence Dead-Air Gap (Shrinks to 0 on Splicing) */}
            {timelineClips.clip1 && timelineClips.clip2 && (
              <div className={`silence-dead-air-gap ${timelineClips.gapClosed ? "is-gap-eliminated" : ""}`}>
                {!timelineClips.gapClosed ? (
                  <span className="dead-air-label">DEAD AIR 2.25s</span>
                ) : (
                  <span className="ripple-closed-badge">RIPPLED</span>
                )}
              </div>
            )}

            {timelineClips.clip2 && (
              <div className={`assembled-clip clip-take-2 ${timelineClips.gapClosed ? "is-rippled-left" : ""}`}>
                <span className="clip-tag">Visual Cut 02</span>
                <span className="clip-time">3.15s - 7.65s</span>
              </div>
            )}

            {/* Laser Blade Slicer Line */}
            {timelineClips.isSplicing && !timelineClips.gapClosed && (
              <div className="dynamic-splicer-laser-line">
                <div className="laser-beam" />
                <div className="laser-sparks" />
              </div>
            )}
          </div>

          {/* Overlay & Audio Lanes */}
          {timelineClips.overlay && (
            <div className="dynamic-assembly-track overlay-track">
              <div className="assembled-clip clip-overlay">
                <span className="clip-tag">Zomato Sticker (PiP)</span>
              </div>
            </div>
          )}

          {timelineClips.audio && (
            <div className="dynamic-assembly-track audio-track">
              <div className="assembled-clip clip-audio">
                <span className="clip-tag">SFX Vine Boom (A1)</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* PHASE 6: Cinema Processing Loading Screen (Clapperboard morphing into Cinema Reel) */}
      {phase === "processing" && (
        <div className="cinema-morph-overlay">
          <div className="cinema-morph-card">
            {/* Clapperboard to Cinema Reel Morph Graphic */}
            <div className="cinema-morph-stage">
              {/* Clapperboard element (snaps shut then morphs) */}
              <div className="clapperboard-morph-container">
                <div className="clapper-stick top-stick" />
                <div className="clapper-stick bottom-stick" />
                <div className="clapper-slate-body">
                  <div className="slate-label">SCENE 01 · TAKE 01</div>
                  <div className="slate-title">INDIC AUTO-CUT</div>
                </div>
              </div>

              {/* Cinema Reel element (morphs in and spins) */}
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

              {/* High-end progress track */}
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

      {/* Floating Status Pill indicating current action */}
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
