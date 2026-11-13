import React from "react";
import "../styles.css";
import "../splic-theme.css";

export const metadata = {
  title: "Splic Studio — Autonomous AI Video Editor for Indic Short-Form",
  description:
    "Autonomous, human-in-the-loop short-form video editor powered by Sarvam AI for Indic creators. 1-click Auto-Cut, Romanized Hinglish subtitles, dynamic stickers, and browser-native WebCodecs export.",
  applicationName: "Splic Studio",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: "/icons/splic-icon.svg",
    apple: "/icons/splic-icon.svg",
  },
  other: {
    google: "notranslate",
    "theme-color": "#0d0f12",
    "color-scheme": "dark",
    "apple-mobile-web-app-capable": "yes",
    "mobile-web-app-capable": "yes",
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" translate="no" className="notranslate" style={{ height: "100%", width: "100%", margin: 0, padding: 0 }}>
      <head>
        <link rel="preconnect" href="https://huggingface.co" crossOrigin="anonymous" />
        <link rel="dns-prefetch" href="https://cdn-lfs.huggingface.co" />
        <link rel="preconnect" href="https://www.modelscope.cn" crossOrigin="anonymous" />
      </head>
      <body suppressHydrationWarning style={{ height: "100%", width: "100%", margin: 0, padding: 0, overflow: "hidden" }}>
        <div id="root" style={{ height: "100%", width: "100%" }}>{children}</div>
      </body>
    </html>
  );
}
