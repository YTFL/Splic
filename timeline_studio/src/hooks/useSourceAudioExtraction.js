import { useCallback } from "react";
import { concatenateAudioBlobs, decodeWaveform, extractAudioFromVideo } from "../lib/media.js";
import { attachSourceAudioOffset, getSourceAudioAssetId } from "../lib/sourceAudioSync.js";
import { loadProjectMediaBlob } from "../lib/projectSnapshot.js";

export function useSourceAudioExtraction(d) {
  return useCallback(async (asset, timelineStart = 0, options = {}) => {
    if (!asset?.blob && !asset?.src && !asset?.projectMedia?.bindings?.blob) { d.notify("Video asset is missing source file, cannot separate audio."); return false; }
    d.setStatus("generating"); d.setStatusText(asset.compatibilityAudioBlob ? d.t("mediaCompatibilityProcessing") : "Loading FFmpeg WASM to separate audio"); d.setProgress(12);
    try {
      const extractedBlob = asset.compatibilityAudioBlob || asset.projectMedia?.bindings?.compatibilityAudioBlob
        ? await loadProjectMediaBlob(asset, "compatibilityAudioBlob")
        : await extractAudioFromVideo(await loadProjectMediaBlob(asset), asset.name);
      d.setStatusText("Analyzing video audio waveform"); d.setProgress(78);
      const extracted = await decodeWaveform(extractedBlob, 96); if (!extracted.duration) throw new Error("Video has no recognizable audio track");
      if (options.destination === "audio") {
        const playbackRate = Math.max(0.25, Math.min(4, Number(asset.playbackRate) || 1));
        const sourceStart = Math.max(0, Number(asset.sourceStart) || 0);
        const timelineDuration = Math.min(
          Math.max(0, Number(asset.duration) || 0),
          asset.speedCurve?.enabled ? asset.duration : Math.max(0, (extracted.duration - sourceStart) / playbackRate),
        );
        if (!(timelineDuration > 0)) throw new Error("Overlay clip has no separable audio range");
        const sourceName = `${asset.name.replace(/\.[^.]+$/, "")} Audio.wav`;
        const audioSegment = d.replaceAudio(extractedBlob, extracted.duration, extracted.peaks, "Overlay audio separated", {
          assetId: getSourceAudioAssetId(asset),
          name: sourceName,
          playbackRate,
          volume: asset.volume ?? 1,
          speedCurve: asset.speedCurve,
          sourceDuration: asset.sourceDuration,
          sourceKind: "overlay-video-audio",
          sourceStart,
          start: timelineStart,
          timelineDuration,
        });
        d.setVisualOverlaySegments?.((segments) => segments.map((segment) => (
          segment.id === asset.id ? { ...segment, muted: true, audioSeparated: true } : segment
        )));
        d.notify("Overlay audio separated to audio track");
        return { track: "audio", segmentId: audioSegment.id };
      }
      const shouldAppend = options.append === true && d.sourceAudioBlob instanceof Blob;
      const sourceAudioOffset = shouldAppend ? Math.max(0, Number(d.sourceAudioDuration) || 0) : 0;
      const sourceAudioAssetId = getSourceAudioAssetId(asset);
      const blob = shouldAppend ? await concatenateAudioBlobs([d.sourceAudioBlob, extractedBlob]) : extractedBlob;
      const decoded = shouldAppend ? await decodeWaveform(blob, 192) : extracted;
      d.setVisualSegments((segments) => attachSourceAudioOffset(segments, asset, sourceAudioOffset));
      const sourceName = shouldAppend ? "Merged Video Audio.wav" : `${asset.name.replace(/\.[^.]+$/, "")} Audio.wav`;
      d.replaceSourceAudio(blob, decoded.duration, decoded.peaks, sourceName, shouldAppend ? "Video audio appended to timeline" : "Video audio separated to timeline", timelineStart, shouldAppend ? "" : sourceAudioAssetId, { focusAudio: false });
      return { track: "source", segmentId: asset.id };
    } catch (error) {
      const message = "Video visual added, but no separable audio track detected.";
      console.warn(error); d.setStatus("ready"); d.setStatusText("No separable audio detected in video");
      d.setProgress(0); d.notify(message);
      return false;
    }
  }, [d]);
}
