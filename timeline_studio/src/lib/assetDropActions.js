import { decodeWaveform, extractVideoTrackFrames, getVideoTrackImportFrameBudget } from "./media.js";
import { getRemoteAssetBlob } from "./remoteAssetCache.js";
import { getVisualInsertionHover, resolveVisualInsertion } from "./visualDropInsertion.js";
import { loadProjectMediaBlob } from "./projectSnapshot.js";
import { resolveAssetDropTrack } from "./assetDragControls.js";
import { getAvailableAudioLane } from "./timeline.js";
import { getSoundEffectsCopy } from "../i18nSoundEffects.js";

function getRemoteVideoImportFrameBudget(duration) {
  const seconds = Math.max(0, Number(duration) || 0);
  const fastFirstPass = seconds > 300 ? 16 : seconds > 120 ? 24 : 48;
  return Math.min(fastFirstPass, getVideoTrackImportFrameBudget(seconds));
}

export function createAssetDropActions(d) {
  const tr = (key, fallback) => d.t?.(key, fallback) ?? fallback;
  async function resolveRemoteAsset(asset, onProgress) {
    if (!asset?.src || asset.blob || !/^https?:/i.test(asset.src)) return asset;
    try {
      d.notify(tr("remoteAssetDownloading", "Downloading online asset…"));
      const blob = await getRemoteAssetBlob(asset, (progress) => {
        d.onRemoteAssetProgress?.(asset.id, progress);
        onProgress?.(progress);
      });
      if (!blob) throw new Error("Missing remote asset");
      const src = URL.createObjectURL(blob);
      d.imageUrlRefs?.current?.add(src);
      return { ...asset, src, blob, remoteSrc: asset.src };
    } catch (error) {
      console.warn("Remote asset download failed", asset?.src || "", error);
      d.notify(tr("remoteAssetDownloadFailed", "Failed to download asset, please retry"));
      return null;
    }
  }

  async function applyAssetToTrack(asset, track, options = {}) {
    if (asset?.type === "audio" && asset.kind === "music") track = "music";
    if (!d.canDropAssetOnTrack(asset, track)) {
      d.notify(tr("assetTrackMismatch", "Drag asset to matching track"));
      return;
    }
    if (asset.kind === "sound-effect") {
      const { audioLane } = options;
      const isDrop = Number.isInteger(audioLane);
      const start = options.startTime ?? d.currentTimeRef.current;
      const copy = getSoundEffectsCopy(d.language);
      let blob = asset.blob;
      if (!blob) {
        try {
          const response = await fetch(asset.src);
          if (!response.ok) throw new Error(response.statusText);
          blob = await response.blob();
          if (!blob.size) throw new Error("Empty sound effect");
        } catch {
          d.notify(copy.unavailable);
          return;
        }
      }
      const { trackLocks, trackVisibility } = d.audioDropTracksRef.current;
      if (trackLocks.audio || trackVisibility.audio === false) return;
      d.checkpointHistory();
      d.pauseForTimelineEdit();
      const segment = d.replaceAudio(blob, asset.duration, asset.peaks, copy.added, {
        start, name: asset.name, sourceKind: asset.kind, assetId: asset.id, seekToStart: !isDrop,
        getLane: (segments) => getAvailableAudioLane(segments, { start, duration: asset.duration }, trackLocks, trackVisibility, audioLane),
      });
      d.revealAudioSegment(segment.id, isDrop);
      d.notify(copy.added);
      return;
    }
    const isRemoteVisual = (track === "image" || track === "overlay") && asset?.src && !asset.blob && /^https?:/i.test(asset.src);
    const hadVisualBefore = Boolean(d.visualSegments?.length);
    let pendingSegment = null;
    let progressBucket = -1;
    if (isRemoteVisual && track === "image") {
      pendingSegment = d.appendVisualAssetToTimeline({
        ...asset,
        preparing: true,
        prepareStage: "download",
        prepareProgress: 0,
      }, { message: tr("remoteAssetDownloading", "Downloading online asset…"), insertIndex: options.insertIndex });
      d.onFirstVisualDropped?.();
    }
    asset = await resolveRemoteAsset(asset, pendingSegment ? (progress) => {
      const bucket = Math.round(Math.max(0, Math.min(1, progress || 0)) * 20) / 20;
      if (bucket === progressBucket) return;
      progressBucket = bucket;
      d.setVisualSegments((segments) => segments.map((segment) => segment.id === pendingSegment.id ? { ...segment, prepareProgress: bucket } : segment));
    } : undefined);
    if (!asset) {
      if (pendingSegment) {
        if (hadVisualBefore) d.setVisualSegments((segments) => segments.filter((segment) => segment.id !== pendingSegment.id));
        else d.clearImageTrack?.(tr("remoteAssetRemovedAfterFailure", "Asset download failed, removed temporary clip"));
      }
      return;
    }
    d.setSelectedLibraryAssetId(asset.id);
    if (track === "sticker") {
      d.addStickerAssetToTimeline(asset, options);
      return;
    }
    if (track === "image") {
      if (pendingSegment) {
        d.updateVisualAssetInTimeline(asset.id, {
          ...asset,
          preparing: asset.type === "video",
          prepareStage: asset.type === "video" ? "prepare" : "",
          prepareProgress: asset.type === "video" ? 0.02 : 1,
        });
        if (asset.type === "video") {
          d.notify(tr("remoteAssetPreparing", "Online asset is preparing"));
          progressBucket = -1;
          let trackFrames = [];
          try {
            trackFrames = await extractVideoTrackFrames(asset.blob || asset.src, {
              duration: asset.duration,
              width: asset.width,
              height: asset.height,
              maxFrames: getRemoteVideoImportFrameBudget(asset.duration),
              // Browser-native seeking is slower per frame but remains PTS-
              // accurate for Wikimedia VP9/WebM files whose sparse WebCodecs
              // seeks can otherwise collapse the strip to repeated frames.
              preferNativeSeek: true,
              onProgress: (progress) => {
                const bucket = Math.round(Math.max(0, Math.min(1, progress || 0)) * 20) / 20;
                if (bucket === progressBucket) return;
                progressBucket = bucket;
                d.setVisualSegments((segments) => segments.map((segment) => segment.id === pendingSegment.id
                  ? { ...segment, prepareStage: "prepare", prepareProgress: bucket }
                  : segment));
              },
            });
          } catch (error) {
            console.warn("Remote video timeline frame extraction failed", error);
          }
          d.updateVisualAssetInTimeline(asset.id, {
            ...(trackFrames.length ? { trackFrames, trackFrameSampling: "exact-pts-hq-v5-seed" } : {}),
            preparing: false,
            prepareStage: "",
            prepareProgress: 1,
            timelineFrameError: !trackFrames.length,
          });
          return;
        }
      } else {
        d.appendVisualAssetToTimeline(asset, { insertIndex: options.insertIndex });
        d.onFirstVisualDropped?.();
      }
      return;
    }
    if (track === "overlay") {
      d.addVisualOverlay?.(asset, options);
      d.onFirstVisualDropped?.();
      return;
    }
    if (track === "music") {
      await d.selectAsset(asset, { focusAudio: false, start: options.startTime });
      return;
    }
    if (track === "audio") {
      let blob;
      try { blob = await loadProjectMediaBlob(asset); }
      catch (error) { console.warn("Audio asset could not be loaded", error); d.notify(tr("audioAssetUnavailable", "Audio asset unavailable, please re-upload")); return; }
      const hasValidDuration = Number.isFinite(Number(asset.duration)) && Number(asset.duration) > 0;
      const decoded = asset.peaks?.length && hasValidDuration
        ? { duration: Number(asset.duration), peaks: asset.peaks }
        : await decodeWaveform(blob, 96);
      const dropStart = Number.isFinite(Number(options.startTime))
        ? Number(options.startTime)
        : Number.isFinite(Number(options.percent)) && Number.isFinite(Number(d.timelineDuration))
          ? Math.max(0, Number(options.percent) / 100 * Number(d.timelineDuration))
          : undefined;
      const { trackLocks, trackVisibility } = d.audioDropTracksRef.current;
      if (trackLocks.audio || trackVisibility.audio === false) return;
      const isDrop = Number.isInteger(options.audioLane);
      const segment = d.replaceAudio(blob, decoded.duration, decoded.peaks, "Audio placed on voiceover track", {
        sourceKind: "upload",
        assetId: asset.id,
        name: asset.name,
        start: dropStart,
        ...(isDrop ? {
          seekToStart: false,
          getLane: (segments) => getAvailableAudioLane(
            segments, { start: dropStart, duration: decoded.duration }, trackLocks, trackVisibility, options.audioLane,
          ),
        } : {}),
      });
      if (isDrop) d.revealAudioSegment(segment.id, true);
      d.setSelectedTrack("audio");
      d.notify(tr("audioDroppedOnVoiceTrack", "Audio placed on voiceover track"));
      return;
    }
    if (track === "source") {
      d.setSelectedTrack("source");
      d.setActiveTool("audio");
      await d.extractVideoSourceAudio(asset);
    }
  }

  function handleTrackAssetDrop(event, track) {
    const asset = d.getDraggedAsset(event);
    const targetTrack = resolveAssetDropTrack(asset, track);
    if (!d.canDropAssetOnTrack(asset, targetTrack)) return;
    event.preventDefault();
    event.stopPropagation();
    const rect = targetTrack === "sticker"
      ? d.trackScrollRef.current?.getBoundingClientRect() ??
        event.currentTarget.getBoundingClientRect()
      : event.currentTarget.getBoundingClientRect();
    const percent = d.getTimelineDropPercent(event.clientX, rect);
    const insertion = targetTrack === "image"
      ? resolveVisualInsertion({
          segments: d.visualSegments,
          percent,
          timelineDuration: d.timelineDuration,
          hover: getVisualInsertionHover(event.target, event.clientX),
        })
      : null;
    d.draggedAssetIdRef.current = "";
    d.setDraggedAssetId("");
    d.setAssetDropTargetTrack("");
    d.setAssetDropPosition({ track: "", percent: 50 });
    if (asset.type === "audio") {
      const placement = d.resolveAudioDrop(event, asset, event.currentTarget, targetTrack);
      d.setSnapGuide(null);
      void applyAssetToTrack(asset, targetTrack, placement);
      return;
    }
    d.triggerAssetDropPulse(targetTrack);
    const startTime = targetTrack === "overlay"
      ? Math.max(0, percent / 100 * Math.max(0, Number(d.timelineDuration) || 0))
      : Number.isFinite(Number(event.currentTarget.dataset.dropStartTime)) ? Number(event.currentTarget.dataset.dropStartTime) : undefined;
    const layer = Number.isFinite(Number(event.currentTarget.dataset.dropLayer)) ? Number(event.currentTarget.dataset.dropLayer) : undefined;
    void applyAssetToTrack(asset, targetTrack, { percent, startTime, layer, insertIndex: insertion?.index });
  }

  function handleVisualStyleDrop(event) {
    const payload = event.dataTransfer?.getData("application/x-timeline-visual-style") || "";
    const [kind, styleId] = payload.split(":");
    if (!styleId || (kind !== "effect" && kind !== "transition")) {
      handleTrackAssetDrop(event, "image");
      return;
    }
    const clip = event.target.closest?.("[data-timeline-segment-id]");
    const segmentId = clip?.dataset.timelineSegmentId;
    if (!segmentId) {
      d.notify("Please drag effect or transition onto a visual clip");
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    d.setVisualSegments((segments) => segments.map((segment) =>
      segment.id === segmentId
        ? { ...segment, [kind === "effect" ? "filterId" : "transitionId"]: styleId }
        : segment,
    ));
    d.setSelectedVisualSegmentId(segmentId);
    d.setSelectedTrack("image");
    if (kind === "effect") d.setSelectedFilterId(styleId);
    else d.setSelectedTransitionId(styleId);
    d.notify(kind === "effect" ? "Effect applied to visual clip" : "Transition applied to clip end");
  }

  return { applyAssetToTrack, handleTrackAssetDrop, handleVisualStyleDrop };
}
