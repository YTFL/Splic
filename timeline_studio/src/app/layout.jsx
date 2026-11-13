import React from "react";
import "../styles.css";
import "../splic-theme.css";

export const metadata = {
  title: "Timeline Studio — Free Browser AI Video Editor & Voiceover Generator",
  description:
    "Create AI voiceovers, automatic captions, talking avatars, and timeline-based videos directly in your browser with Timeline Studio. Local-first editing with MP4 and WebM export.",
  applicationName: "Timeline Studio",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: "/icons/timeline-studio-icon.svg",
    apple: "/icons/timeline-studio-apple-touch.png",
  },
  other: {
    google: "notranslate",
    "theme-color": "#101720",
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
