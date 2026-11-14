export class TtsInputError extends Error {
  constructor(code) {
    super(code);
    this.name = "TtsInputError";
    this.code = code;
  }
}

export function splitTextAtSentenceEnd(rawText) {
  const normalized = normalizeBaseText(rawText);
  if (!normalized) return [];

  if (typeof Intl?.Segmenter === "function") {
    const segmenter = new Intl.Segmenter("en", { granularity: "sentence" });
    const segments = Array.from(segmenter.segment(normalized), ({ segment }) => segment.trim()).filter(Boolean);
    if (segments.length) return segments;
  }

  return normalized
    .match(/[^!?\.\n]+(?:[!?\.]+|(?=\n|$))/g)
    ?.map((segment) => segment.trim())
    .filter(Boolean) ?? [normalized];
}

function countMatches(text, pattern) {
  return text.match(pattern)?.join("").length ?? 0;
}

function normalizeBaseText(text) {
  return text
    .normalize("NFKC")
    .replace(/[\u200B-\u200D\uFEFF]/g, "")
    .replace(/\r\n?/g, "\n")
    .trim();
}

function prepareKokoroText(rawText) {
  const normalized = normalizeBaseText(rawText).replace(/\s+/g, " ");
  const text = normalized.replace(/[^\p{Script=Latin}0-9\s.,!?;:'"()\-]/gu, "").trim();
  if (!text) {
    throw new TtsInputError("ttsErrorNoEnglishContent");
  }

  return {
    text,
    warningKey: text !== normalized ? "ttsWarningEnglishCharactersCleaned" : "",
  };
}

function prepareKokoroMultilangText(rawText) {
  const normalized = normalizeBaseText(rawText);
  const text = normalized
    .replace(/[^\p{Script=Latin}0-9\s,.!?;:\-""''()…—·]/gu, "")
    .replace(/[ \t]+/g, " ")
    .replace(/ *\n+ */g, ". ")
    .replace(/[,]{2,}/g, ", ")
    .replace(/[.!?]{2,}/g, (marks) => marks[0])
    .trim();
  if (!text) throw new TtsInputError("ttsErrorEmptyScript");
  return {
    text,
    warningKey: text !== normalized ? "ttsWarningSymbolsCleaned" : "",
  };
}

export function prepareTextForVoice(rawText, voice) {
  if (voice?.engine === "piper") {
    return prepareKokoroText(rawText);
  }

  if (voice?.engine === "kokoro") {
    return prepareKokoroText(rawText);
  }

  if (voice?.engine === "hojo") {
    return prepareKokoroMultilangText(rawText);
  }

  const text = normalizeBaseText(rawText);
  if (!text) {
    throw new TtsInputError("ttsErrorEmptyScript");
  }
  return { text, warningKey: "" };
}

export function isPiperSymbolError(error) {
  const message = error instanceof Error ? error.message : String(error);
  return /Gather|indices element out of data bounds|OrtRun|emb\/Gather/i.test(message);
}

export function isStorageQuotaError(error) {
  const message = error instanceof Error ? error.message : String(error);
  return /QuotaExceededError|storage quota|exceed.*quota/i.test(message);
}

export async function clearPiperCacheIfStorageTight(tts, voiceId = "") {
  if (!navigator.storage?.estimate || typeof tts?.stored !== "function") {
    return false;
  }

  try {
    const estimate = await navigator.storage.estimate();
    const usage = estimate.usage ?? 0;
    const quota = estimate.quota ?? 0;
    const remaining = quota > usage ? quota - usage : 0;
    if (quota > 0 && (usage / quota > 0.85 || remaining < 200 * 1024 * 1024)) {
      const storedVoices = await tts.stored();
      let cleared = false;
      for (const storedVoice of storedVoices) {
        if (storedVoice === voiceId || typeof tts.remove !== "function") continue;
        await tts.remove(storedVoice);
        cleared = true;
      }
      return cleared;
    }
  } catch {
    return false;
  }

  return false;
}
