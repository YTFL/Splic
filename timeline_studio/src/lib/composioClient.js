/**
 * API client for the Splic backend's Composio integration (`/api/v1/composio/*`).
 *
 * Every request is authenticated with the creator's Firebase ID token. The
 * backend resolves the user identity from that token, so no user id is ever
 * sent from the browser. Requests go through the Next.js rewrite in
 * `next.config.mjs`, which proxies `/api/*` to the FastAPI server on port 8000.
 */

import { getIdToken } from "./firebaseAuth.js";

const API_BASE = "/api/v1";
const OAUTH_MESSAGE_TYPE = "COMPOSIO_OAUTH_SUCCESS";

export class ComposioApiError extends Error {
  constructor(message, { status = 0, code = "" } = {}) {
    super(message);
    this.name = "ComposioApiError";
    this.status = status;
    this.code = code;
  }
}

async function authedRequest(path, { method = "GET", body } = {}) {
  const token = await getIdToken();
  if (!token) {
    throw new ComposioApiError(
      "Sign in with your Splic account to manage connected social platforms.",
      { status: 401, code: "unauthenticated" },
    );
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
  } catch (_error) {
    throw new ComposioApiError(
      "Could not reach the Splic backend. Confirm it is running on port 8000.",
      { code: "network-error" },
    );
  }

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = payload?.detail;
    throw new ComposioApiError(
      typeof detail === "string" && detail ? detail : "The backend could not complete this request.",
      { status: response.status, code: payload?.error_type || "" },
    );
  }

  return payload;
}

/** List every account connected by the signed-in creator, optionally by toolkit. */
export function getConnectedAccounts(toolkit) {
  const query = toolkit ? `?toolkit=${encodeURIComponent(toolkit)}` : "";
  return authedRequest(`/composio/accounts${query}`);
}

/** Start the Instagram OAuth flow; resolves with `{ redirect_url, connection_request_id }`. */
export function initiateInstagramConnect(redirectUrl) {
  return authedRequest("/composio/connect/instagram", {
    method: "POST",
    body: { redirect_url: redirectUrl },
  });
}

/**
 * YouTube scopes needed to publish. The read-only scope alone can list a channel
 * but never upload, so the upload scope must be granted when connecting.
 */
export const YOUTUBE_PUBLISH_SCOPES = [
  "https://www.googleapis.com/auth/youtube.upload",
  "https://www.googleapis.com/auth/youtube.readonly",
];

/** Start the YouTube OAuth flow; resolves with `{ redirect_url, connection_request_id }`. */
export function initiateYouTubeConnect(redirectUrl, scopes = YOUTUBE_PUBLISH_SCOPES) {
  return authedRequest("/composio/connect/youtube", {
    method: "POST",
    body: { redirect_url: redirectUrl, scopes },
  });
}

/** Disconnect (revoke) a connected account owned by the signed-in creator. */
export function disconnectAccount(accountId) {
  return authedRequest(`/composio/accounts/${encodeURIComponent(accountId)}`, { method: "DELETE" });
}

/** Check whether the creator has an active connection for a toolkit. */
export function checkToolkitStatus(toolkit) {
  return authedRequest(`/composio/connect/${encodeURIComponent(toolkit)}/status`);
}

async function authedMultipartRequest(path, formData) {
  const token = await getIdToken();
  if (!token) {
    throw new ComposioApiError(
      "Sign in with your Splic account before publishing.",
      { status: 401, code: "unauthenticated" },
    );
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });
  } catch (_error) {
    throw new ComposioApiError(
      "Could not reach the Splic backend. Confirm it is running on port 8000.",
      { code: "network-error" },
    );
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail;
    throw new ComposioApiError(
      typeof detail === "string" && detail ? detail : "The backend could not publish this video.",
      { status: response.status, code: payload?.error_type || "" },
    );
  }
  return payload;
}

/** Publish a rendered reel to Instagram (creates and publishes a Reels container). */
export function publishToInstagram({ file, fileName, caption, shareToFeed = true, accountId }) {
  const form = new FormData();
  form.append("file", file, fileName || "reel.mp4");
  form.append("caption", caption || "");
  form.append("share_to_feed", shareToFeed ? "true" : "false");
  if (accountId) form.append("account_id", accountId);
  return authedMultipartRequest("/publish/instagram", form);
}

/** Upload a rendered reel to YouTube. */
export function publishToYouTube({
  file,
  fileName,
  title,
  description = "",
  tags = [],
  privacy = "public",
  categoryId = "22",
  accountId,
}) {
  const form = new FormData();
  form.append("file", file, fileName || "reel.mp4");
  form.append("title", title || "Splic Studio Reel");
  form.append("description", description || "");
  form.append("tags", (tags || []).join(","));
  form.append("privacy_status", privacy || "public");
  form.append("category_id", categoryId);
  if (accountId) form.append("account_id", accountId);
  return authedMultipartRequest("/publish/youtube", form);
}

/**
 * Map the backend's connected-account list onto the studio's `connectedSocials`
 * shape. Only Instagram and YouTube are backed by Composio; the other platforms
 * keep whatever local state they already had.
 */
export function mapAccountsToSocialState(accounts = [], previous = {}) {
  const activeAccounts = (accounts || []).filter((account) => {
    if (!account) return false;
    if (typeof account.is_active === "boolean") return account.is_active;
    return String(account.status || "").toUpperCase() === "ACTIVE";
  });

  const next = { ...previous };

  for (const toolkit of ["instagram", "youtube"]) {
    const match = activeAccounts.find(
      (account) => String(account.toolkit || "").toLowerCase() === toolkit,
    );
    next[toolkit] = {
      name:
        previous[toolkit]?.name ||
        (toolkit === "instagram" ? "Instagram Reels" : "YouTube Shorts & Video"),
      connected: Boolean(match),
      handle: match ? match.account_handle || match.account_name || "" : "",
      accountId: match?.id || "",
      status: match?.status || (match ? "ACTIVE" : "NOT_CONNECTED"),
    };
  }

  return next;
}

/** Absolute callback URL the OAuth popup returns to once the creator authorizes. */
export function buildOAuthCallbackUrl(toolkit) {
  const origin = typeof window === "undefined" ? "" : window.location.origin;
  return `${origin}/auth/callback?toolkit=${encodeURIComponent(toolkit)}`;
}

/** Open the Composio authorization page in a secure popup that keeps `window.opener`. */
export function openOAuthPopup(url) {
  if (typeof window === "undefined") return null;
  const width = 520;
  const height = 700;
  const left = Math.max(0, window.screenX + (window.outerWidth - width) / 2);
  const top = Math.max(0, window.screenY + (window.outerHeight - height) / 2);
  return window.open(
    url,
    "splic-composio-oauth",
    `width=${width},height=${height},left=${left},top=${top},scrollbars=yes,resizable=yes`,
  );
}

export { OAUTH_MESSAGE_TYPE };
