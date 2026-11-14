// Source coordinates remain in the script. Only the resulting clip/caption
// operations carry composition coordinates; each occurrence gets its own ID.
export function scriptEditOperations(record, assets, visualCount, timelineOffset, makeId = () => crypto.randomUUID()) {
  if (!record.confirmed || !record.sourcesCurrent) throw new Error("Please confirm the script and source media first.");
  const sources = new Map(record.draft.sources.map(source => [source.sourceId, source]));
  const includedKinds = new Set(record.draft.content.segments.filter(segment => segment.included)
    .flatMap(segment => segment.sourceIds.map(id => sources.get(id)?.kind)));
  if (includedKinds.has("audio") && includedKinds.size > 1) throw new Error("Script mixes audio and video; clarify audio-visual alignment before submitting plan.");
  const operations = [], mappings = [];
  let atIndex = visualCount, cursor = timelineOffset;
  for (const segment of record.draft.content.segments.filter(segment => segment.included)) {
    if (segment.kind === "narration") throw new Error("Script contains narration; generate and bind voiceover before submitting plan.");
    if (segment.sourceIds.length !== 1) throw new Error("Segment contains multiple source ranges; specify a single source range per segment.");
    const source = sources.get(segment.sourceIds[0]);
    const asset = assets.find(asset => (asset.assetId || asset.id) === source?.assetRef.entityId);
    if (!source || !asset) throw new Error("Script source asset has not loaded yet.");
    const start = source.range.sourceStartSeconds, end = source.range.sourceEndSeconds;
    const duration = source.kind === "image" ? segment.estimatedDurationSeconds : end - start;
    if (!Number.isFinite(duration) || duration < 0.2) throw new Error("Script source range is too short or invalid.");
    const clipId = makeId();
    if (source.kind === "audio") {
      operations.push({ type: "asset.insert", assetId: source.assetRef.entityId, clipId, track: "audio", start: cursor });
      operations.push({ type: "timed.trim", track: "audio", clipId, sourceIn: start, sourceOut: end });
    } else {
      operations.push({ type: "visual.insert", assetId: source.assetRef.entityId, clipId, atIndex: atIndex++, ...(source.kind === "image" ? { duration } : {}) });
      if (source.kind === "video") operations.push({ type: "visual.trim", clipId, sourceIn: start, sourceOut: end });
    }
    if (segment.kind === "sourceSpeech" && segment.editedText) operations.push({ type: "caption.add", clipId: makeId(),
      text: segment.editedText, start: cursor, end: cursor + duration,
      ...(source.kind === "audio" ? { audioClipId: clipId } : { visualClipId: clipId }) });
    mappings.push({ segmentId: segment.segmentId, sourceId: source.sourceId, clipId,
      sourceStartSeconds: start, sourceEndSeconds: end, timelineStartSeconds: cursor, timelineEndSeconds: cursor + duration });
    cursor += duration;
  }
  if (!operations.length) throw new Error("The script has no included clips to edit.");
  return { operations, mappings };
}
