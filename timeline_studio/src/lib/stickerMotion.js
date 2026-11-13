// Sticker in / out / emphasis animation.
//
// A sticker segment may carry:
//   animation: { in: { id, duration }, out: { id, duration } }  -> the editor's own clip
//              animations (fade / zoom / slide-left / slide-up, lib/visualClipAnimations.js)
//   motion:    { in, out, emphasis }                            -> animations the editor has no
//              native version of (pop / bounce / spin in, pop out, wiggle / pulse emphasis),
//              built here as keyframes relative to the sticker's own transform.
// Keyframes are generated from the ids and the segment's current duration, so
// resizing or restyling a sticker on the timeline keeps its animation intact.
import { resolveVisualClipAnimation } from "./visualClipAnimations.js";
import { resolveVisualTransform } from "./visualEffects.js";

export const STICKER_MOTION_IN_IDS = Object.freeze(["pop", "bounce", "spin"]);
export const STICKER_MOTION_OUT_IDS = Object.freeze(["pop"]);
export const STICKER_EMPHASIS_IDS = Object.freeze(["wiggle", "pulse"]);

const IN_SECONDS = { pop: 0.35, bounce: 0.6, spin: 0.5 };
const OUT_SECONDS = { pop: 0.3 };
const UNIT = { scale: 1, rotation: 0, opacity: 1, x: 0, y: 0 };
const frameCache = new WeakMap();

const finite = (value, fallback) => (Number.isFinite(Number(value)) ? Number(value) : fallback);

/** Relative keyframes ({time, scale: factor, rotation: degrees delta, opacity: factor}) for a sticker. */
export function buildStickerMotionFrames(motion = {}, duration = 0, nativeAnimation = {}) {
  const d = Math.max(0.1, finite(duration, 0.1));
  const budget = Math.max(0.2, d * 0.4);
  const frames = new Map();
  const kf = (time, values) => {
    const t = Math.round(Math.max(0, Math.min(d, time)) * 1000) / 1000;
    frames.set(t, { ...(frames.get(t) || {}), ...values });
  };
  const inId = STICKER_MOTION_IN_IDS.includes(motion.in) ? motion.in : "";
  const outId = STICKER_MOTION_OUT_IDS.includes(motion.out) ? motion.out : "";
  const inD = Math.min(IN_SECONDS[inId] || 0, budget);
  const outD = Math.min(OUT_SECONDS[outId] || 0, budget);

  if (inId === "pop") {
    kf(0, { scale: 0.2, opacity: 0 });
    kf(0.6 * inD, { scale: 1.18, opacity: 1 });
    kf(inD, { scale: 1 });
  } else if (inId === "bounce") {
    kf(0, { scale: 0.3, opacity: 0 });
    kf(0.25 * inD, { scale: 1.15, opacity: 1 });
    kf(0.5 * inD, { scale: 0.92 });
    kf(0.75 * inD, { scale: 1.05 });
    kf(inD, { scale: 1 });
  } else if (inId === "spin") {
    kf(0, { scale: 0.3, rotation: -180, opacity: 0 });
    kf(inD, { scale: 1, rotation: 0, opacity: 1 });
  }
  const nativeIn = nativeAnimation?.in?.id && nativeAnimation.in.id !== "none" ? finite(nativeAnimation.in.duration, 0.4) : 0;
  const nativeOut = nativeAnimation?.out?.id && nativeAnimation.out.id !== "none" ? finite(nativeAnimation.out.duration, 0.4) : 0;
  const inEnd = Math.max(inD, Math.min(nativeIn, budget));
  const outStart = d - Math.max(outD, Math.min(nativeOut, budget));

  if (outId === "pop") {
    kf(d - outD, { scale: 1, opacity: 1 });
    kf(d - outD + 0.35 * outD, { scale: 1.12 });
    kf(d, { scale: 0.2, opacity: 0 });
  }

  const holdStart = inEnd + 0.05;
  const holdEnd = outStart - 0.05;
  if (motion.emphasis === "wiggle" && holdEnd - holdStart >= 0.5) {
    [8, -8, 6, -4, 0].forEach((delta, index) => kf(holdStart + index * 0.1, { rotation: delta }));
  } else if (motion.emphasis === "pulse" && holdEnd - holdStart >= 0.5) {
    const mid = (holdStart + holdEnd) / 2;
    kf(mid - 0.18, { scale: 1 });
    kf(mid, { scale: 1.1 });
    kf(mid + 0.18, { scale: 1 });
  }
  return [...frames.entries()].sort((a, b) => a[0] - b[0]).map(([time, values]) => ({ time, ...values }));
}

function hasMotion(sticker) {
  const motion = sticker?.motion;
  const animation = sticker?.animation;
  return Boolean(
    (motion && (motion.in || motion.out || motion.emphasis))
    || (animation && ((animation.in?.id && animation.in.id !== "none") || (animation.out?.id && animation.out.id !== "none"))),
  );
}

function framesFor(sticker) {
  const key = `${sticker.motion?.in}|${sticker.motion?.out}|${sticker.motion?.emphasis}|${sticker.duration}|${sticker.animation?.in?.id}:${sticker.animation?.in?.duration}|${sticker.animation?.out?.id}:${sticker.animation?.out?.duration}`;
  const cached = frameCache.get(sticker);
  if (cached?.key === key) return cached.frames;
  const frames = sticker.motion ? buildStickerMotionFrames(sticker.motion, sticker.duration, sticker.animation) : [];
  frameCache.set(sticker, { key, frames });
  return frames;
}

/** Relative transform of a sticker `localTime` seconds after it starts. */
export function resolveStickerMotion(sticker, localTime) {
  if (!hasMotion(sticker)) return UNIT;
  const duration = Math.max(0.01, finite(sticker.duration, 0.01));
  const time = Math.max(0, Math.min(duration, finite(localTime, 0)));
  const keyed = resolveVisualTransform(framesFor(sticker), time, { x: 0, y: 0, scale: 1, rotation: 0, opacity: 1 });
  const native = resolveVisualClipAnimation(sticker.animation, time, duration);
  return {
    x: native.x,
    y: native.y,
    scale: keyed.scale * native.scale,
    rotation: keyed.rotation,
    opacity: keyed.opacity * native.opacity,
  };
}

/** The sticker as it should be drawn at `timelineTime` (same object when it has no animation). */
export function animateStickerAtTime(sticker, timelineTime) {
  if (!sticker || !hasMotion(sticker)) return sticker;
  const m = resolveStickerMotion(sticker, finite(timelineTime, 0) - finite(sticker.start, 0));
  if (m === UNIT) return sticker;
  return {
    ...sticker,
    x: finite(sticker.x, 82) + m.x,
    y: finite(sticker.y, 20) + m.y,
    scale: finite(sticker.scale, 1) * m.scale,
    rotation: finite(sticker.rotation, 0) + m.rotation,
    opacity: Math.max(0, Math.min(1, finite(sticker.opacity, 1) * m.opacity)),
    motionBase: sticker, // editing handles read the un-animated transform
  };
}
