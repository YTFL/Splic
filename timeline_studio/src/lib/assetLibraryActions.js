import { decodeWaveform } from "./media.js";
import { loadProjectMediaBlob, isProjectMediaBlob } from "./projectSnapshot.js";

export function createAssetLibraryActions(deps) {
  async function selectAsset(asset, options = {}) {
    if (asset.type === "audio") {
      let blob;
      try { blob = await loadProjectMediaBlob(asset); }
      catch (error) { console.warn("Audio asset could not be loaded", error); deps.notify(deps.t?.("audioAssetUnavailable") || "Audio asset unavailable"); return; }
      asset.blob = blob;
      const hasValidDuration = Number.isFinite(Number(asset.duration)) && Number(asset.duration) > 0;
      const decoded = asset.peaks?.length && hasValidDuration
        ? { duration: Number(asset.duration), peaks: asset.peaks }
        : await decodeWaveform(blob, 96);
      deps.replaceMusic(
        blob,
        decoded.duration,
        decoded.peaks,
        asset.name,
        undefined,
        { focusAudio: options.focusAudio !== false, start: options.start },
      );
      return;
    }
    deps.replaceVisualTimeline(asset, deps.getVisualDurationForAsset(asset));
    deps.notify(`${asset.type === "video" ? "Video" : "Image"} asset applied to preview and timeline`);
  }

  function deleteUserAsset(asset) {
    deps.removeVisionRecordsForAsset(asset);
    const urlInUse = deps.userAssets.some((item) => item.id !== asset.id && item.src === asset.src);
    if (deps.selectedLibraryAssetId === asset.id) deps.setSelectedLibraryAssetId("");
    deps.setUserAssets((items) => items.filter((item) => item.id !== asset.id));
    if (!urlInUse && deps.imageUrlRefs.current.has(asset.src)) {
      URL.revokeObjectURL(asset.src); deps.imageUrlRefs.current.delete(asset.src);
    }
    if (asset.type === "audio" && ((asset.blob && asset.blob === deps.musicBlob) || isProjectMediaBlob(asset, deps.musicBlob))) {
      deps.clearMusicTrack("Background music deleted; timeline cleared");
      return;
    }
    const isActiveVisual = asset.type !== "audio" && (asset.src === deps.imageSrc ||
      deps.visualSegments.some((segment) => segment.assetId === asset.id || segment.src === asset.src));
    if (!isActiveVisual) return void deps.notify("Asset deleted");
    const segments = deps.visualSegments.filter((segment) => segment.assetId !== asset.id && segment.src !== asset.src);
    if (asset.type === "video" && deps.sourceAudioBlob && asset.src === deps.imageSrc) deps.clearSourceAudioTrack(null);
    if (segments.length) deps.commitVisualSegments(segments, "Asset deleted, corresponding visual clip removed");
    else deps.clearImageTrack("Visual asset deleted, timeline cleared");
  }
  return { deleteUserAsset, selectAsset };
}
