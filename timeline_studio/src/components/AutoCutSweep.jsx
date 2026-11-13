// Post-processing Auto-Cut editing animation.
//
// After the processing screen closes, App sweeps the editor's real playhead from
// 0 s to the end of the clip and drops each JSON edit (captions, stickers, SFX,
// effects) onto the timeline the moment the sweep reaches it. This component is
// the only extra UI: the original status pill, a glow on clips as they arrive,
// and a flash on the video track whenever the sweep crosses a cut point.
// No full-screen layer, canvas or backdrop: the editor is always visible.
import { useEffect } from "react";
import { Zap } from "lucide-react";
import "./AutoCutSweep.css";

const ARRIVAL_SELECTOR = ".image-clip, .caption-segment, .sticker-segment, .audio-clip, .timeline-effect-clip";

function formatTime(seconds) {
  const s = Math.max(0, Number(seconds) || 0);
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${(s % 60).toFixed(1).padStart(4, "0")}`;
}

function useTimelineArrivals(active) {
  useEffect(() => {
    if (!active || typeof MutationObserver === "undefined") return undefined;
    const timers = new Set();
    const mark = (element) => {
      element.classList.add("auto-cut-arrive");
      const timer = window.setTimeout(() => {
        element.classList.remove("auto-cut-arrive");
        timers.delete(timer);
      }, 900);
      timers.add(timer);
    };
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (!(node instanceof Element)) continue;
          if (node.matches(ARRIVAL_SELECTOR)) mark(node);
          node.querySelectorAll?.(ARRIVAL_SELECTOR).forEach(mark);
        }
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    return () => {
      observer.disconnect();
      timers.forEach((timer) => window.clearTimeout(timer));
    };
  }, [active]);
}

function useSeamFlash(flash) {
  useEffect(() => {
    if (!flash) return undefined;
    const track = document.querySelector(".image-track") || document.querySelector(".tracks");
    if (!track) return undefined;
    track.classList.remove("auto-cut-seam-flash");
    void track.offsetWidth; // restart the animation for back-to-back cuts
    track.classList.add("auto-cut-seam-flash");
    const timer = window.setTimeout(() => track.classList.remove("auto-cut-seam-flash"), 520);
    return () => window.clearTimeout(timer);
  }, [flash]);
}

export function AutoCutSweep({ sweep }) {
  useTimelineArrivals(Boolean(sweep));
  useSeamFlash(sweep?.flash || 0);
  if (!sweep) return null;
  return (
    <div className="assembly-status-pill auto-cut-sweep-pill" role="status" aria-live="polite">
      <div className="assembly-pulse-icon">
        <Zap size={13} strokeWidth={1.5} />
      </div>
      <span>{sweep.text}</span>
      {sweep.total > 0 ? (
        <span className="auto-cut-sweep-time">{formatTime(sweep.time)} / {formatTime(sweep.total)}</span>
      ) : null}
    </div>
  );
}
