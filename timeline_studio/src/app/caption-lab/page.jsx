"use client";

import { useState } from "react";
import { CaptionOverlay } from "../../components/CaptionOverlay.jsx";

export default function CaptionLab() {
  const [opacity, setOpacity] = useState(0.5);
  const [fontId, setFontId] = useState("default");
  const [text, setText] = useState("Ye toh full paisa vasool hai");
  const style = {
    textColor: "#ffffff",
    backgroundColor: "#000000",
    backgroundOpacity: opacity,
    borderColor: "#35f0dd",
    borderWidth: 0,
    radius: 7,
    paddingX: 22,
    paddingY: 12,
    shadowOpacity: 0.45,
    effect: "normal",
    textStrokeColor: "#05080d",
    textStrokeWidth: 0,
    fontId,
  };
  return (
    <div style={{ padding: 24 }}>
      <div
        id="lab-frame"
        style={{ position: "relative", width: 640, height: 360, background: "#8fb3d9" }}
      >
        <CaptionOverlay
          text={text}
          captionSize={28}
          captionStyle={style}
          placement={{ x: 50, y: 78 }}
          frameSize={{ width: 640, height: 360 }}
        />
      </div>
      <label>
        opacity
        <input
          id="lab-opacity"
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={opacity}
          onChange={(event) => setOpacity(Number(event.target.value))}
        />
        <span id="lab-opacity-value">{opacity}</span>
      </label>
      <label>
        font
        <select id="lab-font" value={fontId} onChange={(event) => setFontId(event.target.value)}>
          <option value="default">default</option>
          <option value="poppins">poppins</option>
        </select>
      </label>
      <label>
        text
        <input id="lab-text" value={text} onChange={(event) => setText(event.target.value)} />
      </label>
    </div>
  );
}
