// Auto-Cut dispatcher: talks to the FastAPI backend (/api/sarvam-auto-edit,
// proxied same-origin by next.config.mjs) and translates the returned EditPlan
// into editable Timeline Studio track items.
//
// Clock contract: every EditPlan timestamp is float seconds on the ORIGINAL
// source clock of the uploaded file. We map source time -> timeline time for the
// target clip, then collapse overlay times through the ripple cuts ourselves
// (Strategy B), because the cut itself is applied by the existing silence-removal
// review, which only ripples items that already exist on the timeline.
import { MIN_VISUAL_SEGMENT_SECONDS } from "../config/editor.js";
import { collapseTime } from "./silenceRemoval.js";
import { createStickerSegment, getAvailableAudioLane } from "./timeline.js";
import { decodeWaveform } from "./media.js";

const EPS = 0.000001;
const MIN_ITEM_SECONDS = 0.1;

export const AUTO_CUT_ENDPOINT = "/api/sarvam-auto-edit";

// Progress text shown in the modal and in the agentic animation sweep.
export const AUTO_CUT_LIVE_STATUS = {
  uploading: "Sarvam Saaras is transcribing and the director is planning the edit (usually 2-3 minutes)...",
  assets: "Plan received: loading stickers and SFX...",
  assembling: "Applying cuts, captions, stickers and SFX to the timeline...",
};

/** Backend EditPlan (schemas.EditPlan) vs. the legacy demo JSON used by AutoEditEngine. */
export function isBackendEditPlan(plan) {
  if (!plan || typeof plan !== "object") return false;
  return Boolean(
    plan.director
    || Array.isArray(plan.words)
    || plan.captions?.some?.((caption) => Array.isArray(caption?.words))
    || plan.stickers?.some?.((sticker) => typeof sticker?.asset_url === "string"),
  );
}

const PLAN_KEYS = ["cuts", "captions", "stickers", "sfx", "zooms", "words"];
const WRAPPER_KEYS = ["edit_plan", "editPlan", "plan", "data", "result", "response"];

/**
 * Find the EditPlan inside uploaded JSON: a bare plan, or one nested under a
 * wrapper such as a saved project ({ edit_plan }) or an API envelope ({ data }).
 * Returns null when nothing plan-shaped is present.
 */
export function extractEditPlan(json, depth = 0) {
  if (!json || typeof json !== "object" || Array.isArray(json) || depth > 3) return null;
  if (PLAN_KEYS.some((key) => Array.isArray(json[key]) && json[key].length)) return json;
  for (const key of WRAPPER_KEYS) {
    const found = extractEditPlan(json[key], depth + 1);
    if (found) return found;
  }
  return null;
}

/** Pick the clip the auto-cut should operate on: the selected video, else the first video. */
export function findAutoCutTargetClip(visualSegments = [], selectedSegment = null) {
  const index = selectedSegment?.type === "video"
    ? visualSegments.findIndex((clip) => clip.id === selectedSegment.id)
    : visualSegments.findIndex((clip) => clip.type === "video");
  if (index < 0) return null;
  const start = visualSegments.slice(0, index).reduce((sum, clip) => sum + (Number(clip.duration) || 0), 0);
  return { clip: visualSegments[index], index, start };
}

async function loadClipBlob(clip) {
  if (clip?.blob instanceof Blob && clip.blob.size) return clip.blob;
  const src = clip?.src || clip?.url;
  if (!src) throw new Error("The selected video has no readable media source");
  const response = await fetch(src);
  if (!response.ok) throw new Error(`Could not read the timeline video (${response.status})`);
  return response.blob();
}

/** POST the clip's media to the backend and return the validated EditPlan JSON. */
export async function requestAutoCutEditPlan(clip, { languageCode = "hi-IN", fetchStickers = true, signal } = {}) {
  const blob = await loadClipBlob(clip);
  const form = new FormData();
  form.append("file", blob, clip.name || "timeline-video.mp4");
  form.append("language_code", languageCode);
  form.append("fetch_stickers", String(fetchStickers));
  let response;
  try {
    response = await fetch(AUTO_CUT_ENDPOINT, { method: "POST", body: form, signal });
  } catch (error) {
    if (error?.name === "AbortError") throw error;
    throw new Error("Auto-Cut backend is unreachable. Start it with: uvicorn main:app --port 8000", { cause: error });
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = typeof body?.detail === "string" ? body.detail : JSON.stringify(body?.detail ?? body);
    } catch { /* non-JSON error body */ }
    throw new Error(`Auto-Cut backend error (${response.status}): ${detail}`);
  }
  return response.json();
}

const num = (value) => (Number.isFinite(Number(value)) ? Number(value) : NaN);

/**
 * Pure mapping from an EditPlan onto one clip of the timeline.
 * Returns cut candidates relative to the clip (silence-removal format) and a
 * `toTimeline(sourceTime, { collapsed })` mapper for overlay items.
 */
export function planClipMapping(plan, target) {
  const { clip, start: clipStart } = target;
  const rate = Number(clip.playbackRate) || 1;
  const sourceStart = Number(clip.sourceStart) || 0;
  const clipDuration = Number(clip.duration) || 0;
  const toClip = (time) => (time - sourceStart) / rate;

  // Clamp, merge, and keep only cuts that leave valid clip pieces on both sides.
  const raw = (plan.cuts || [])
    .map((cut) => ({ start: Math.max(0, toClip(num(cut.start))), end: Math.min(clipDuration, toClip(num(cut.end))), reason: cut.reason }))
    .filter((cut) => Number.isFinite(cut.start) && Number.isFinite(cut.end) && cut.end - cut.start >= MIN_VISUAL_SEGMENT_SECONDS)
    .sort((a, b) => a.start - b.start);
  const merged = [];
  for (const cut of raw) {
    const last = merged[merged.length - 1];
    if (last && cut.start <= last.end + EPS) last.end = Math.max(last.end, cut.end);
    else merged.push({ ...cut });
  }
  const candidates = [];
  let cursor = 0;
  for (const cut of merged) {
    if (cut.start > cursor + EPS && cut.start - cursor < MIN_VISUAL_SEGMENT_SECONDS) continue;
    if (cut.end < clipDuration - EPS && clipDuration - cut.end < MIN_VISUAL_SEGMENT_SECONDS) continue;
    if (cut.end - cut.start > clipDuration - MIN_VISUAL_SEGMENT_SECONDS) continue;
    candidates.push({ id: `auto-cut-${candidates.length}`, start: cut.start, end: cut.end, enabled: true, reason: cut.reason });
    cursor = cut.end;
  }
  const timelineCuts = candidates.map((cut) => ({ start: clipStart + cut.start, end: clipStart + cut.end }));

  const toTimeline = (sourceTime, { collapsed = true } = {}) => {
    const local = toClip(num(sourceTime));
    if (!Number.isFinite(local)) return NaN;
    const clamped = Math.min(Math.max(local, 0), clipDuration);
    const time = clipStart + clamped;
    return collapsed ? collapseTime(time, timelineCuts) : time;
  };
  const inClip = (sourceTime) => {
    const local = toClip(num(sourceTime));
    return Number.isFinite(local) && local >= -EPS && local < clipDuration - MIN_ITEM_SECONDS;
  };
  return { candidates, timelineCuts, toTimeline, inClip, clipStart, clipDuration };
}

/** EditPlan captions -> Timeline Studio caption segments (karaoke words kept on the segment). */
export function buildAutoCutCaptionSegments(plan, mapping) {
  return (plan.captions || []).flatMap((caption, index) => {
    if (!caption?.text || !mapping.inClip(caption.start)) return [];
    const start = mapping.toTimeline(caption.start);
    const end = mapping.toTimeline(caption.end);
    if (!(end - start >= MIN_ITEM_SECONDS)) return [];
    const words = (caption.words || []).map((word) => ({
      word: word.word,
      start: mapping.toTimeline(word.start_time),
      end: mapping.toTimeline(word.end_time),
    })).filter((word) => word.word && word.end > word.start);
    return [{
      id: `auto-cut-caption-${index}-${crypto.randomUUID().slice(0, 8)}`,
      text: String(caption.text),
      start: Number(start.toFixed(3)),
      end: Number(end.toFixed(3)),
      weight: "bold",
      hidden: false,
      fontId: "default",
      ...(words.length ? { words } : {}),
      ...(caption.highlight_color ? { highlightColor: caption.highlight_color } : {}),
    }];
  });
}

/** EditPlan stickers -> sticker-track segments (positions are 0-1 in the plan, percent here). */
export function buildAutoCutStickerSegments(plan, mapping) {
  return (plan.stickers || []).flatMap((sticker) => {
    const src = sticker?.asset_url || sticker?.asset;
    if (!src || !mapping.inClip(sticker.start)) return [];
    const start = mapping.toTimeline(sticker.start);
    const end = mapping.toTimeline(num(sticker.start) + (num(sticker.duration) || 2));
    if (!(end - start >= MIN_ITEM_SECONDS)) return [];
    const x = num(sticker.position?.x);
    const y = num(sticker.position?.y);
    return [createStickerSegment({
      stickerId: `auto-cut-${sticker.slug || sticker.keyword}`,
      name: sticker.keyword || "Sticker",
      nameEn: sticker.keyword || "Sticker",
      category: "auto-cut",
      src,
      x: Number.isFinite(x) ? (x <= 1 ? x * 100 : x) : undefined,
      y: Number.isFinite(y) ? (y <= 1 ? y * 100 : y) : undefined,
      scale: Number.isFinite(num(sticker.scale)) ? num(sticker.scale) : 1,
    }, Number(start.toFixed(3)), Number((end - start).toFixed(3)))];
  });
}

/**
 * Fetch + decode each distinct SFX asset once. Assets that fail to load are
 * reported instead of crashing the dispatch (AGENTS.md Rule 6).
 */
export async function preloadAutoCutSfx(plan) {
  const decodedByAsset = new Map();
  const failed = [];
  for (const asset of new Set((plan.sfx || []).map((sfx) => sfx?.asset).filter(Boolean))) {
    try {
      const response = await fetch(asset);
      if (!response.ok) throw new Error(response.statusText);
      const blob = await response.blob();
      const wave = await decodeWaveform(blob, 96);
      decodedByAsset.set(asset, { blob, duration: wave.duration, peaks: wave.peaks });
    } catch {
      failed.push(asset.split("/").pop());
    }
  }
  return { decodedByAsset, failed };
}

/** EditPlan sfx -> audio-track segments, using assets from preloadAutoCutSfx(). */
export function buildAutoCutSfxSegments(plan, mapping, decodedByAsset, { existingSegments = [], trackLocks, trackVisibility } = {}) {
  const segments = [];
  for (const sfx of plan.sfx || []) {
    if (!sfx?.asset || !mapping.inClip(sfx.start)) continue;
    const decoded = decodedByAsset.get(sfx.asset);
    if (!decoded) continue;
    const start = Number(mapping.toTimeline(sfx.start).toFixed(3));
    const duration = Number(decoded.duration) || 1;
    const segment = {
      id: crypto.randomUUID(),
      blob: decoded.blob,
      url: URL.createObjectURL(decoded.blob),
      start,
      duration,
      sourceStart: 0,
      sourceDuration: duration,
      playbackRate: 1,
      peaks: decoded.peaks || [],
      volume: Math.max(0, Math.min(4, Number.isFinite(num(sfx.volume)) ? num(sfx.volume) : 1)),
      fadeIn: 0,
      fadeOut: 0,
      reversed: false,
      name: sfx.label ? `SFX: ${sfx.label}` : "SFX",
      sourceKind: "upload",
      voiceId: "",
      voiceName: "",
      cloneVoiceProfileId: "",
      cloneVoiceProfileName: "",
      assetId: "",
    };
    const lane = getAvailableAudioLane([...existingSegments, ...segments], { start, duration }, trackLocks, trackVisibility);
    segments.push(Number.isInteger(lane) ? { ...segment, lane } : segment);
  }
  return segments;
}
