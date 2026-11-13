// Special Effects catalog pool with dedicated color palettes and physics configs
export const SPECIAL_EFFECTS_POOL = [
  {
    id: "glitch",
    name: "Glitch Cut",
    effect: "glitch",
    color: "#f5c542",
    colorPalette: ["#f5c542", "#e6a13c", "#ffffff", "#8b5212", "#3a2508"],
    intensity: 0.95,
  },
  {
    id: "ripple",
    name: "Liquid Ripple",
    effect: "ripple",
    color: "#e53935",
    colorPalette: ["#e53935", "#d32f2f", "#ffffff", "#b71c1c", "#ffebee"],
    intensity: 0.95,
    ripple: {
      enabled: true,
      bpm: 120,
      interval: 0.5,
      radius: 10,
      colorAmount: 0.9,
      glow: 0.85,
      color: "#e53935",
    },
  },
  {
    id: "shake",
    name: "Camera Shake",
    effect: "shake",
    color: "#f97316",
    colorPalette: ["#f97316", "#c2410c", "#fed7aa", "#7c2d12", "#fff7ed"],
    intensity: 0.95,
    beat: { source: "tempo", bpm: 140, subdivision: 2 },
  },
  {
    id: "chromatic",
    name: "RGB Chromatic Split",
    effect: "chromatic",
    color: "#e53935",
    colorPalette: ["#e53935", "#d32f2f", "#f43f5e", "#ffffff", "#2d0b13"],
    intensity: 0.95,
  },
  {
    id: "glow",
    name: "Luminous Glow",
    effect: "glow",
    color: "#eab308",
    colorPalette: ["#fbbf24", "#d97706", "#fef3c7", "#78350f", "#ffffff"],
    intensity: 0.95,
  },
];

// Pre-packaged Sarvam AI Indic Video Director EditPlan for testing
export const SAMPLE_EDIT_PLAN = {
  cuts: [
    { start: 3.15, end: 4.95, reason: "Dead air silence & Indic hesitation" },
  ],
  captions: [
    {
      id: "caption-1",
      start: 0.35,
      end: 3.05,
      text: "Aaj hum baat karenge top AI tools ke baare mein",
    },
    {
      id: "caption-2",
      start: 3.25,
      end: 7.45,
      text: "Jo aapke workflow ko 10x fast kar denge",
    },
  ],
  stickers: [
    {
      keyword: "Zomato",
      asset: "/assets/stickers/trend-flame.png",
      start: 1.25,
      duration: 2.2,
      position: { x: 0.5, y: 0.3 },
    },
  ],
  sfx: [
    {
      asset: "/assets/sound-effects/bell-hit.mp3",
      start: 3.25,
      volume: 1.0,
    },
  ],
  effects: [
    {
      type: "glitch",
      start: 2.75,
      duration: 1.4,
      intensity: 0.95,
    },
  ],
  zooms: [{ start: 3.25, end: 4.0, scale: 1.25 }],
};

// Validates and normalizes any incoming Sarvam AI Director EditPlan JSON into timeline tracks
export function normalizeEditPlan(input, userAssets = []) {
  if (!input) {
    throw new Error("No edit plan provided");
  }

  let plan = input;
  if (typeof input === "string") {
    try {
      plan = JSON.parse(input);
    } catch (_err) {
      throw new Error("Failed to parse edit plan: Invalid JSON string", { cause: _err });
    }
  }

  if (typeof plan !== "object" || plan === null) {
    throw new Error("Invalid edit plan format: Expected JSON object");
  }

  // Validate that instructions contain at least one recognized directive
  const hasCuts = Array.isArray(plan.cuts) && plan.cuts.length > 0;
  const hasCaptions = Array.isArray(plan.captions) && plan.captions.length > 0;
  const hasStickers = Array.isArray(plan.stickers) && plan.stickers.length > 0;
  const hasSfx = Array.isArray(plan.sfx) && plan.sfx.length > 0;
  const hasEffects = Array.isArray(plan.effects) && plan.effects.length > 0;
  const hasMedia = plan.media && plan.media.cut1;

  if (!hasCuts && !hasCaptions && !hasStickers && !hasSfx && !hasEffects && !hasMedia) {
    throw new Error("Incompatible JSON instructions: Missing cuts, captions, stickers, or sfx");
  }

  const asset0 = userAssets[0] || {
    id: "asset-raw-sample-01",
    name: "Camera_A_Speaker_Main.mp4",
    type: "image",
    src: "/assets/sample-portrait.png",
  };
  const asset1 = userAssets[1] || {
    id: "asset-raw-sample-02",
    name: "B_Roll_Studio_Setup.mp4",
    type: "image",
    src: "/assets/smart/auto-edit-card-bg.webp",
  };
  const asset2 = userAssets[2] || {
    id: "asset-raw-sample-03",
    name: "Zomato_UPI_Promo.png",
    type: "image",
    src: "/assets/stickers/trend-flame.png",
  };
  const asset3 = userAssets[3] || {
    id: "asset-raw-sample-04",
    name: "SFX_Vine_Boom.mp3",
    type: "audio",
    src: "/assets/sound-effects/bell-hit.mp3",
  };

  const cuts = Array.isArray(plan.cuts) ? plan.cuts : [];
  const primaryCut = cuts[0] || { start: 3.15, end: 4.95, reason: "Dead air silence" };
  const duration1 = Number(Number(primaryCut.start || 3.15).toFixed(2));
  const cutEnd = Number(Number(primaryCut.end || (duration1 + 1.8)).toFixed(2));
  const gapDuration = Number(Math.max(0.5, cutEnd - duration1).toFixed(2));
  const duration2 = Number(Number(plan.duration2 || (plan.totalDuration ? Math.max(1, plan.totalDuration - cutEnd) : 4.2)).toFixed(2));

  // Layer-distinct palettes
  const paletteMediaA = ["#d59b72", "#bc7c4f", "#8b5a3c", "#3e3b38", "#e8ded1"];
  const paletteMediaB = ["#c2653c", "#944422", "#473c35", "#d68c45", "#2a2d34"];
  const paletteSticker = ["#cb202d", "#b51c27", "#8c1d24", "#e89297", "#f3f4f6"];
  const paletteAudio = ["#58a065", "#3d7a48", "#88d497", "#bfe8c5", "#1f3823"];

  // Effect from JSON or fallback
  const effectData = (Array.isArray(plan.effects) ? plan.effects[0] : null) || plan.effect || {};
  const requestedEffect = (effectData.type || effectData.effect || "glitch").toLowerCase();
  const matchedEffect = SPECIAL_EFFECTS_POOL.find((fx) => fx.effect === requestedEffect) || SPECIAL_EFFECTS_POOL[0];

  // Sticker from JSON or fallback
  const stickerData = (Array.isArray(plan.stickers) ? plan.stickers[0] : null) || plan.sticker || {};
  const stickerAsset = stickerData.asset
    ? {
        id: "sticker-json-asset",
        name: stickerData.keyword ? `${stickerData.keyword} Sticker` : "Cultural Sticker Cutout",
        type: "image",
        src: stickerData.asset,
      }
    : asset2;

  // SFX from JSON or fallback
  const sfxData = (Array.isArray(plan.sfx) ? plan.sfx[0] : null) || plan.audio || {};
  const audioAsset = sfxData.asset
    ? {
        id: "sfx-json-asset",
        name: sfxData.name || "SFX Sound Effect",
        type: "audio",
        src: sfxData.asset,
      }
    : asset3;

  // Captions from JSON or fallback
  const captionsList = Array.isArray(plan.captions) && plan.captions.length > 0 ? plan.captions : [
    {
      id: `caption-1-${Date.now()}`,
      start: 0.35,
      end: duration1 - 0.15,
      text: "Aaj hum baat karenge top AI tools ke baare mein",
    },
    {
      id: `caption-2-${Date.now()}`,
      start: duration1 + 0.1,
      end: duration1 + duration2 - 0.2,
      text: "Jo aapke workflow ko 10x fast kar denge",
    },
  ];

  return {
    isAltOrder: Boolean(plan.isAltOrder),
    cuts: cuts.length > 0 ? cuts : [primaryCut],
    media: {
      cut1: {
        asset: plan.media?.cut1?.asset || asset0,
        assetIndex: 0,
        start: 0,
        duration: duration1,
        name: plan.media?.cut1?.name || `${asset0.name} [Take 01]`,
        colorPalette: paletteMediaA,
      },
      cut2: {
        asset: plan.media?.cut2?.asset || asset1,
        assetIndex: 1,
        start: duration1,
        duration: duration2,
        name: plan.media?.cut2?.name || `${asset1.name} [Take 02]`,
        colorPalette: paletteMediaB,
      },
    },
    deadAir: {
      start: duration1,
      duration: gapDuration,
    },
    effect: {
      id: effectData.id || `fx-${matchedEffect.effect}-${Date.now()}`,
      name: matchedEffect.name,
      effect: matchedEffect.effect,
      color: matchedEffect.color,
      colorPalette: matchedEffect.colorPalette,
      intensity: effectData.intensity || matchedEffect.intensity,
      beat: matchedEffect.beat,
      ripple: matchedEffect.ripple,
      start: effectData.start ?? Math.max(0, Number((duration1 - 0.4).toFixed(2))),
      duration: effectData.duration || 1.4,
      at: duration1,
    },
    sticker: {
      id: stickerData.id || "sticker-entity",
      keyword: stickerData.keyword || "Sticker",
      name: stickerAsset.name,
      asset: stickerAsset,
      assetIndex: 2,
      start: stickerData.start ?? Number((1.2).toFixed(2)),
      duration: stickerData.duration || 2.2,
      colorPalette: paletteSticker,
      position: stickerData.position || { x: 0.5, y: 0.3 },
    },
    audio: {
      id: sfxData.id || "sfx-vine-boom",
      name: audioAsset.name,
      asset: audioAsset,
      assetIndex: 3,
      start: sfxData.start ?? Number((duration1 + 0.1).toFixed(2)),
      duration: sfxData.duration || 1.6,
      volume: sfxData.volume ?? 1.0,
      colorPalette: paletteAudio,
    },
    captions: captionsList,
    zooms: Array.isArray(plan.zooms) ? plan.zooms : [],
  };
}

