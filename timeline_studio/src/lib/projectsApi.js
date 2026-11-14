// Projects stored in the backend TinyDB (~/.splic/db.json) via FastAPI,
// proxied same-origin by next.config.mjs (/api -> http://localhost:8000/api).
const PROJECTS_ENDPOINT = "/api/projects";

// Where the backend reads projects from (db.json, stickers/, runs/), from the last list call.
let lastStoragePaths = null;
export const getStoragePaths = () => lastStoragePaths;

const PLATFORM_LABELS = {
  "9:16": "Instagram Reel",
  "16:9": "YouTube Video",
  "1:1": "Square Post",
  "4:5": "Portrait Feed",
};

async function readError(response) {
  try {
    const body = await response.json();
    return typeof body?.detail === "string" ? body.detail : response.statusText;
  } catch {
    return response.statusText;
  }
}

/** Backend project document (+ summary built from ~/.splic storage) -> dashboard card. */
export function toDashboardProject(doc) {
  const settings = doc?.settings || {};
  const summary = doc?.summary || {};
  const ratioId = settings.ratioId || settings.aspect_ratio || "9:16";
  const plan = doc?.edit_plan || null; // only present on single-project responses
  const updated = Date.parse(doc?.updated_at || doc?.created_at || "");
  const counts = summary.counts || {};
  return {
    id: doc.id,
    name: doc.name || "Untitled Project",
    ratioId,
    platform: settings.platformPreset || settings.platform || PLATFORM_LABELS[ratioId] || ratioId,
    fps: settings.fps || 30,
    languageMode: settings.languageMode,
    duration: Number(summary.duration) || Number(plan?.duration) || Number(settings.duration) || 0,
    updatedAt: Number.isFinite(updated) ? updated : Date.now(),
    createdAt: Date.parse(doc?.created_at || "") || null,
    thumbnail: settings.thumbnail || summary.stickers?.thumbnail || "/assets/sample-portrait.png",
    status: summary.status || doc.status || "draft",
    director: summary.director || null,
    counts: {
      cuts: counts.cuts || 0, captions: counts.captions || 0, stickers: counts.stickers || 0,
      sfx: counts.sfx || 0, transitions: counts.transitions || 0, zooms: counts.zooms || 0, effects: counts.effects || 0,
    },
    stickerFiles: summary.stickers?.on_disk || 0,
    runs: summary.runs?.count || 0,
    latestRun: summary.runs?.latest || null,
    hasEditPlan: Boolean(summary.has_edit_plan || plan),
    hasCaptions: Boolean(counts.captions || plan?.captions?.length),
    clipsCount: summary.has_edit_plan || plan ? 1 : 0,
  };
}

/** All stored projects, most recently updated first. */
export async function fetchProjects({ signal } = {}) {
  const response = await fetch(PROJECTS_ENDPOINT, { signal });
  if (!response.ok) throw new Error(`Could not load projects (${response.status}): ${await readError(response)}`);
  const body = await response.json();
  lastStoragePaths = body?.storage || null;
  return (Array.isArray(body?.projects) ? body.projects : [])
    .filter((doc) => doc && doc.id)
    .map(toDashboardProject)
    .sort((a, b) => b.updatedAt - a.updatedAt);
}

/** Persist a project created in the New Project dialog. */
export async function createStoredProject(project) {
  const response = await fetch(PROJECTS_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: project.name,
      project_id: project.id,
      settings: {
        aspect_ratio: project.ratioId,
        ratioId: project.ratioId,
        platformPreset: project.platformPreset || project.platform,
        fps: project.fps,
        languageMode: project.languageMode,
      },
    }),
  });
  if (!response.ok) throw new Error(`Could not save project (${response.status}): ${await readError(response)}`);
  return toDashboardProject(await response.json());
}

/** Delete a stored project (and its sticker links). A project already gone counts as deleted. */
export async function deleteStoredProject(projectId) {
  const response = await fetch(`${PROJECTS_ENDPOINT}/${encodeURIComponent(projectId)}`, { method: "DELETE" });
  if (!response.ok && response.status !== 404) {
    throw new Error(`Could not delete project (${response.status}): ${await readError(response)}`);
  }
}
