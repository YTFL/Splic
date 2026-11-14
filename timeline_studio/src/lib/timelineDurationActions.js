import { getVideoSourceEndCopy } from "../i18nCaptionEditing.js";
import { getVisualSourceDurationLimit } from "./visualSourceLimit.js";
import { MAX_TIMELINE_DURATION_SECONDS, MIN_VISUAL_SEGMENT_SECONDS } from "../config/editor.js";
import { createVisualSegment, getVisualSegmentsTotal, hasExplicitCaptionTiming } from "./timeline.js";

export function createTimelineDurationActions(d) {
  return function adjustSelectedSegmentWeight(delta) {
    if (d.selectedTrack === "sticker") {
      if (d.trackLocks.sticker) return void d.notify("Sticker track is locked, cannot adjust duration");
      const selected = d.selectedStickerSegmentId ? d.stickerSegments.findIndex((segment) => segment.id === d.selectedStickerSegmentId) : -1;
      const index = selected >= 0 ? selected : d.currentStickerSegmentIndex >= 0 ? d.currentStickerSegmentIndex : 0;
      const source = d.stickerSegments[index]; if (!source) return void d.notify("Please select a sticker clip");
      const duration = Math.max(MIN_VISUAL_SEGMENT_SECONDS, Math.min(MAX_TIMELINE_DURATION_SECONDS - source.start, source.duration + (delta > 0 ? 0.5 : -0.5)));
      if (Math.abs(duration - source.duration) < 0.001) return void d.notify(delta > 0 ? "Sticker clip is at max duration" : "Sticker clip is at minimum duration");
      const next = d.stickerSegments.map((segment, position) => position === index ? { ...segment, duration } : segment);
      return void d.commitStickerSegments(next, delta > 0 ? "Sticker clip lengthened" : "Sticker clip shortened", source.id);
    }
    if (d.selectedTrack === "image") {
      if (d.trackLocks.image) return void d.notify("Visual track is locked, cannot adjust duration");
      if (!d.imageSrc) return void d.notify("Please upload or select media first");
      const source = d.visualSegments.length ? d.visualSegments : [createVisualSegment(d.imageDuration || 4, d.getCurrentVisualAssetSnapshot())];
      const index = d.selectedVisualSegmentId && source.some((segment) => segment.id === d.selectedVisualSegmentId)
        ? d.selectedVisualSegmentIndex : d.currentVisualSegmentIndex >= 0 ? d.currentVisualSegmentIndex : source.length - 1;
      const target = source[index]; const without = getVisualSegmentsTotal(source) - target.duration;
      const max = Math.min(getVisualSourceDurationLimit(target), Math.max(MIN_VISUAL_SEGMENT_SECONDS, MAX_TIMELINE_DURATION_SECONDS - without));
      const duration = Math.min(max, Math.max(MIN_VISUAL_SEGMENT_SECONDS, target.duration + (delta > 0 ? 1 : -1)));
      if (duration === target.duration && delta > 0 && target.type === "video" && max < MAX_TIMELINE_DURATION_SECONDS - without) return void d.notify(getVideoSourceEndCopy(d.uiLanguage));
      if (duration === target.duration) return void d.notify(delta > 0 ? "Visual track reached 30-minute limit" : "Visual clip is at minimum duration");
      const next = source.map((segment, position) => position === index ? {
        ...segment,
        duration,
        ...(segment.type === "video" ? { sourceDuration: duration * Math.max(0.25, Math.min(4, Number(segment.playbackRate) || 1)) } : {}),
      } : segment);
      d.rippleTimelineAfter?.(getVisualSegmentsTotal(source.slice(0, index + 1)), duration - target.duration);
      return void d.commitVisualSegments(next, delta > 0 ? "Visual clip lengthened" : "Visual clip shortened", index);
    }
    if (d.selectedTrack === "music") return void d.notify("Music duration is set by the asset; trimming and fades supported");
    if (d.selectedTrack === "source") return void d.notify("Source audio duration is set by video; splitting supported");
    if (d.selectedTrack !== "caption") return void d.notify("Please select a caption segment to adjust length");
    if (!d.captionSegments.length) return void d.notify("No captions available to adjust");
    if (d.trackLocks.caption) return void d.notify("Caption track is locked, cannot adjust duration");
    const index = d.selectedSegmentId ? d.selectedSegmentIndex : d.focusedSegmentIndex;
    const target = d.captionSegments[index];
    if (hasExplicitCaptionTiming(target)) {
      const nextTimed = d.captionSegments.slice(index + 1).find(hasExplicitCaptionTiming);
      const maxEnd = Math.min(MAX_TIMELINE_DURATION_SECONDS, nextTimed?.start ?? MAX_TIMELINE_DURATION_SECONDS);
      const end = Math.max(target.start + 0.45, Math.min(maxEnd, target.end + (delta > 0 ? 0.6 : -0.6)));
      if (Math.abs(end - target.end) < 0.001) return void d.notify(delta > 0 ? "Caption is touching the next segment" : "Caption is at minimum duration");
      const next = d.captionSegments.map((segment, position) => position === index ? { ...segment, end } : segment);
      return void d.commitCaptionSegments(next, delta > 0 ? "Caption lengthened" : "Caption shortened", index);
    }
    const next = d.captionSegments.map((segment, position) => position === index
      ? { ...segment, weight: Math.max(0.5, Math.min(5, (segment.weight ?? 1) + delta)) } : segment);
    d.commitCaptionSegments(next, delta > 0 ? "Caption segment extended" : "Caption segment shortened", index);
  };
}
