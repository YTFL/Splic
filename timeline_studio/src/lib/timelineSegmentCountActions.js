import { DEFAULT_STICKER_SEGMENT_SECONDS, IMAGE_SEGMENT_SECONDS, MAX_TIMELINE_DURATION_SECONDS, MIN_VISUAL_SEGMENT_SECONDS } from "../config/editor.js";
import { createStickerSegment, createVisualSegment, getVisualSegmentTimeline, getVisualSegmentsTotal, makeId } from "./timeline.js";

export function createTimelineSegmentCountActions(d) {
  const stickerIndex = () => {
    const selected = d.selectedStickerSegmentId ? d.stickerSegments.findIndex((segment) => segment.id === d.selectedStickerSegmentId) : -1;
    return selected >= 0 ? selected : d.currentStickerSegmentIndex >= 0 ? d.currentStickerSegmentIndex : 0;
  };
  const deleteSticker = () => {
    if (!d.stickerSegments.length) return void d.notify("No sticker clips to delete");
    const index = stickerIndex(); const next = d.stickerSegments.filter((_, position) => position !== index);
    d.commitStickerSegments(next, next.length ? "Deleted current sticker clip" : "Deleted last sticker clip", next[Math.max(0, index - 1)]?.id ?? "");
  };
  const handleAddCaptionSegment = (requestedStart = null) => {
    if (d.trackLocks.caption) return void d.notify(d.t?.("captionTrackLocked") ?? "Caption track is locked, cannot add caption");
    const insertionTime = Number.isFinite(requestedStart) ? requestedStart : d.currentTime;
    const start = Math.max(0, Math.min(MAX_TIMELINE_DURATION_SECONDS - 0.45, insertionTime));
    const previousSegment = [...d.captionSegments]
      .sort((left, right) => (Number(left.start) || 0) - (Number(right.start) || 0))
      .filter((item) => (Number(item.start) || 0) <= start)
      .at(-1);
    // This explicit Add action targets the main picture under the insertion
    // point. Record ownership now rather than guessing from overlap on delete.
    const owner = getVisualSegmentTimeline(d.visualSegments || []).find(range => start >= range.start && start < range.end && range.end - start >= 0.2);
    const segment = { id: makeId("caption"), text: d.t?.("newCaptionDefault") ?? "New caption segment", weight: 1, hidden: false,
      fontId: previousSegment?.fontId || d.captionStyle?.fontId || "default",
      ...(owner ? { visualSegmentId: owner.id } : {}),
      start, end: Math.min(MAX_TIMELINE_DURATION_SECONDS, start + 1.8, owner?.end ?? Infinity) };
    const next = [...d.captionSegments, segment].sort((a, b) => (Number(a.start) || 0) - (Number(b.start) || 0));
    d.commitCaptionSegments(next, Number.isFinite(requestedStart) ? "Added caption at clicked position" : "Added caption at playhead", next.findIndex((item) => item.id === segment.id));
  };
  const handleAddSegment = (requestedStart = null) => {
    if (d.selectedTrack === "sticker") {
      if (d.trackLocks.sticker) return void d.notify("Sticker track is locked, cannot add sticker");
      const source = d.stickerSegments[stickerIndex()] ?? d.getStickerDragAsset(d.selectedSticker);
      if (!source?.src) return void d.notify("Please select a sticker first");
      const segment = createStickerSegment(source, d.currentTime, DEFAULT_STICKER_SEGMENT_SECONDS);
      const owner = getVisualSegmentTimeline(d.visualSegments || []).find(range => d.currentTime >= range.start && d.currentTime < range.end && range.end - d.currentTime >= MIN_VISUAL_SEGMENT_SECONDS);
      if (owner) { segment.visualSegmentId = owner.id; segment.duration = Math.min(segment.duration, owner.end - d.currentTime); }
      return void d.commitStickerSegments([...d.stickerSegments, segment], "Added sticker clip", segment.id);
    }
    if (d.selectedTrack === "image") {
      if (d.trackLocks.image) return void d.notify("Visual track is locked, cannot add clip");
      if (!d.imageSrc) return void d.notify("Please upload or select media first");
      const source = d.visualSegments.length ? d.visualSegments : [createVisualSegment(d.imageDuration || 4, d.getCurrentVisualAssetSnapshot())];
      const available = MAX_TIMELINE_DURATION_SECONDS - getVisualSegmentsTotal(source);
      if (available < MIN_VISUAL_SEGMENT_SECONDS) return void d.notify("Visual track reached 30-minute limit");
      const timeline = getVisualSegmentTimeline(source);
      const playhead = Math.max(0, Math.min(getVisualSegmentsTotal(source), d.currentTime));
      const activeIndex = timeline.findIndex((range) => playhead >= range.start && playhead < range.end);
      const selectedIndex = d.selectedVisualSegmentId && source.some((segment) => segment.id === d.selectedVisualSegmentId)
        ? d.selectedVisualSegmentIndex
        : activeIndex >= 0 ? activeIndex : source.length - 1;
      const asset = source[selectedIndex] ?? d.getCurrentVisualAssetSnapshot();
      const segment = createVisualSegment(Math.min(IMAGE_SEGMENT_SECONDS, available), asset);
      const boundaryIndex = timeline.findIndex((range) => Math.abs(range.start - playhead) < 0.001);
      if (boundaryIndex >= 0) {
        const next = [...source]; next.splice(boundaryIndex, 0, segment);
        d.rippleTimelineAfter?.(playhead, segment.duration);
        return void d.commitVisualSegments(next, "Added visual clip at playhead", boundaryIndex);
      }
      const range = timeline[activeIndex]; const active = source[activeIndex];
      if (range && active && playhead > range.start && playhead < range.end) {
        const leftDuration = playhead - range.start; const rightDuration = range.end - playhead;
        if (leftDuration < MIN_VISUAL_SEGMENT_SECONDS || rightDuration < MIN_VISUAL_SEGMENT_SECONDS) {
          return void d.notify("Playhead is too close to clip edge, please move slightly");
        }
        const playbackRate = active.type === "video" ? Math.max(0.25, Math.min(4, Number(active.playbackRate) || 1)) : 1;
        const left = { ...active, id: makeId("visual"), duration: leftDuration,
          sourceDuration: active.type === "video" ? leftDuration * playbackRate : active.sourceDuration };
        const right = { ...active, id: makeId("visual"), duration: rightDuration,
          sourceDuration: active.type === "video" ? rightDuration * playbackRate : active.sourceDuration,
          sourceStart: active.type === "video" ? Math.max(0, Number(active.sourceStart) || 0) + leftDuration * playbackRate : Math.max(0, Number(active.sourceStart) || 0) };
        const next = [...source]; next.splice(activeIndex, 1, left, segment, right);
        d.rippleTimelineAfter?.(playhead, segment.duration);
        return void d.commitVisualSegments(next, "Added visual clip at playhead", activeIndex + 1);
      }
      d.rippleTimelineAfter?.(getVisualSegmentsTotal(source), segment.duration);
      return void d.commitVisualSegments([...source, segment], "Added visual clip at playhead", source.length);
    }
    if (["audio", "source", "music"].includes(d.selectedTrack)) return void d.notify(d.selectedTrack === "music" ? "Background music does not support slicing, please delete or re-upload" : d.selectedTrack === "source" ? "Source audio does not support slicing, re-upload or split on timeline" : "Audio clips are determined by generated audio, please regenerate or edit");
    return handleAddCaptionSegment(requestedStart);
  };
  const handleRemoveSegment = () => {
    if (d.selectedTrack === "sticker") return void deleteSticker();
    if (d.selectedTrack === "image") {
      if (d.trackLocks.image) return void d.notify("Visual track is locked, cannot remove clip");
      if (!d.imageSrc || d.imageClipCount === 0) return void d.notify("No visual clips to remove");
      const source = d.visualSegments.length ? d.visualSegments : [createVisualSegment(d.imageDuration || 0, d.getCurrentVisualAssetSnapshot())];
      if (source.length > 1) {
        const index = d.selectedVisualSegmentId && source.some((segment) => segment.id === d.selectedVisualSegmentId) ? d.selectedVisualSegmentIndex : d.currentVisualSegmentIndex >= 0 ? d.currentVisualSegmentIndex : source.length - 1;
        const removed = source[index];
        d.rippleTimelineAfter?.(getVisualSegmentsTotal(source.slice(0, index + 1)), -removed.duration);
        return void d.commitVisualSegments(source.filter((_, position) => position !== index), "Deleted visual clip", Math.max(0, index - 1), [removed.id]);
      }
      if (source[0].duration <= IMAGE_SEGMENT_SECONDS) {
        d.rippleTimelineAfter?.(source[0].duration, -source[0].duration);
        return void d.clearImageTrack("Deleted last visual clip", [source[0].id]);
      }
      d.rippleTimelineAfter?.(source[0].duration, -IMAGE_SEGMENT_SECONDS);
      return void d.commitVisualSegments([{ ...source[0], duration: source[0].duration - IMAGE_SEGMENT_SECONDS }], "Shortened visual clip", 0);
    }
    if (["audio", "source", "music"].includes(d.selectedTrack)) return void d.notify(d.selectedTrack === "music" ? "Background music can be deleted on track header" : d.selectedTrack === "source" ? "Source audio can be deleted on track header" : "Audio clips cannot be reduced individually; clear track or regenerate");
    if (!d.captionSegments.length) return void d.notify("No captions available to delete");
    d.deleteCaptionSegment(d.selectedSegmentId);
  };
  return { handleAddCaptionSegment, handleAddSegment, handleRemoveSegment };
}
