"use client";

import React, { useEffect, useState } from "react";
import { CheckCircle2, Loader2 } from "lucide-react";

import { OAUTH_MESSAGE_TYPE } from "../../../lib/composioClient.js";

/**
 * OAuth return route for Composio authorization popups.
 *
 * Composio redirects the authorization popup here. The page hands a single
 * message to the window that opened it (the Settings modal), then closes itself
 * so the creator lands back on their untouched timeline state.
 */
export default function OAuthCallbackPage() {
  const [phase, setPhase] = useState("connecting"); // "connecting" | "done" | "standalone"
  const [toolkit, setToolkit] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const requestedToolkit = params.get("toolkit") || params.get("app") || "";
    setToolkit(requestedToolkit);

    const opener = window.opener;
    if (!opener || opener.closed) {
      setPhase("standalone");
      return;
    }

    try {
      opener.postMessage(
        { type: OAUTH_MESSAGE_TYPE, toolkit: requestedToolkit, status: "success" },
        window.location.origin,
      );
    } catch (_error) {
      // Cross-window messaging can fail if the opener navigated away mid-flow.
    }

    setPhase("done");
    const timer = window.setTimeout(() => window.close(), 900);
    return () => window.clearTimeout(timer);
  }, []);

  const platformLabel = toolkit
    ? toolkit.charAt(0).toUpperCase() + toolkit.slice(1)
    : "social account";

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "14px",
        background: "#0d0f12",
        color: "#f4f4f5",
        fontFamily: "inherit",
        textAlign: "center",
        padding: "32px",
      }}
    >
      {phase === "connecting" ? (
        <Loader2 size={26} strokeWidth={1.25} className="spin-icon" style={{ color: "#e11d48" }} />
      ) : (
        <CheckCircle2 size={26} strokeWidth={1.25} style={{ color: "#4ade80" }} />
      )}

      <h1 style={{ margin: 0, fontSize: "16px", fontWeight: 700 }}>
        {phase === "connecting" ? "Completing authorization" : `${platformLabel} authorization complete`}
      </h1>

      <p style={{ margin: 0, fontSize: "12px", color: "#9ca3af", maxWidth: "360px" }}>
        {phase === "standalone"
          ? "You can close this tab and return to Splic Studio. The connected account will appear in Studio Settings."
          : "Returning to Splic Studio and refreshing your connected accounts."}
      </p>
    </main>
  );
}
