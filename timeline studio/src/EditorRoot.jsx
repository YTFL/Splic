"use client";

import React, { useEffect, useState } from "react";
import { App } from "./App.jsx";
import { registerModelCacheServiceWorker } from "./lib/serviceWorker.js";
import { connectHostSession } from "./lib/hostSession.js";
import { getStoredLanguage } from "./i18n.js";
import { hostText } from "./i18nHost.js";
import "./styles.css";

export default function EditorRoot() {
  const [hostSession, setHostSession] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    registerModelCacheServiceWorker();
    void connectHostSession()
      .then((session) => {
        if (session) setHostSession(session);
      })
      .catch(() => {
        setError(hostText(getStoredLanguage(), "expired"));
      });
  }, []);

  if (error) {
    return (
      <div style={{ display: "flex", height: "100vh", width: "100vw", alignItems: "center", justifyContent: "center", background: "#07090d", color: "#eef5f7" }}>
        <p role="alert">{error}</p>
      </div>
    );
  }

  return <App hostSession={hostSession} />;
}
