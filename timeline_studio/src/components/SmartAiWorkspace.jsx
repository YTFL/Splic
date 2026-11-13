import React, { useState } from "react";
import {
  Scissors,
  Subtitles,
  Smile,
  Mic,
  Music,
  Zap,
  CheckCircle2,
  RefreshCw,
} from "lucide-react";

export function SmartAiWorkspace({
  autoEdit,
  silenceRemoval,
  aiMusic,
  onRunAutoCut,
  isProcessingAutoCut = false,
  autoCutProgress = 0,
  autoCutPhase = "",
  t = (k, fallback) => fallback || k,
  activeLanguage = "en",
  onApplyCaptions,
  onApplySilenceCuts,
  hasVisual = false,
}) {
  const [activeAiTab, setActiveAiTab] = useState("auto-cut");
  const [silenceThreshold, setSilenceThreshold] = useState(0.8);
  const [captionMode, setCaptionMode] = useState("romanized"); // "romanized" | "dual"
  const [autoCutStatus, setAutoCutStatus] = useState("idle"); // "idle" | "running" | "success"

  const aiTabs = [
    { id: "auto-cut", label: "Auto-Cut", icon: Zap, highlight: true },
    { id: "silence", label: "Silence & Cuts", icon: Scissors },
    { id: "captions", label: "Romanized Captions", icon: Subtitles },
    { id: "stickers", label: "Dynamic Stickers", icon: Smile },
    { id: "voice", label: "Indic Voiceover", icon: Mic },
    { id: "music", label: "AI Music & Audio", icon: Music },
  ];

  const handleTriggerAutoCut = async () => {
    setAutoCutStatus("running");
    if (onRunAutoCut) {
      try {
        await onRunAutoCut({ captionMode, silenceThreshold });
        setAutoCutStatus("success");
      } catch (err) {
        setAutoCutStatus("idle");
      }
    } else {
      setTimeout(() => {
        setAutoCutStatus("success");
      }, 2000);
    }
  };

  return (
    <div className="smart-ai-container">
      {/* Smart AI Sub-tabs */}
      <div className="smart-ai-tabs" role="tablist">
        {aiTabs.map(({ id, label, icon: Icon, highlight }) => {
          const isActive = activeAiTab === id;
          return (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={isActive}
              className={`smart-ai-tab ${isActive ? "is-active" : ""} ${highlight ? "is-highlight" : ""}`}
              onClick={() => setActiveAiTab(id)}
            >
              <Icon size={14} strokeWidth={isActive ? 1.75 : 1.25} />
              <span>{label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab 1: Auto-Cut Pipeline */}
      {activeAiTab === "auto-cut" && (
        <div className="smart-ai-content">
          <div className="smart-hero-banner">
            <div className="smart-hero-icon">
              <Zap size={22} strokeWidth={1.5} />
            </div>
            <div className="smart-hero-text">
              <div className="hero-title-row">
                <h3>Auto-Cut</h3>
              </div>
              <p>
                1-Click autonomous video editor for Indic short-form creators. Automatically transcribes code-mixed speech (Hinglish/Tamil/Telugu), removes dead-air silences, burns Romanized phonetic captions, overlays Indian cultural stickers, and injects meme SFX.
              </p>
            </div>
          </div>

          <div className="smart-config-card">
            <h4>Pipeline Configuration</h4>
            
            <div className="smart-config-row">
              <label>Caption Output Script</label>
              <div className="smart-segmented-pills">
                <button
                  type="button"
                  className={`pill-btn ${captionMode === "romanized" ? "is-active" : ""}`}
                  onClick={() => setCaptionMode("romanized")}
                >
                  Romanized Indic (Hinglish)
                </button>
                <button
                  type="button"
                  className={`pill-btn ${captionMode === "dual" ? "is-active" : ""}`}
                  onClick={() => setCaptionMode("dual")}
                >
                  Dual (Hinglish + English)
                </button>
              </div>
            </div>

            <div className="smart-config-row">
              <label>Dead-Air Silence Cut Threshold: {silenceThreshold}s</label>
              <input
                type="range"
                min="0.3"
                max="2.0"
                step="0.1"
                value={silenceThreshold}
                onChange={(e) => setSilenceThreshold(parseFloat(e.target.value))}
                className="smart-slider"
              />
            </div>

            <div className="smart-feature-list">
              <div className="feature-item">
                <CheckCircle2 size={13} strokeWidth={1.5} />
                <span>Saaras v4 Millisecond-level Word Timestamps</span>
              </div>
              <div className="feature-item">
                <CheckCircle2 size={13} strokeWidth={1.5} />
                <span>Sarvam-105B Video Director LLM Edit Plan</span>
              </div>
              <div className="feature-item">
                <CheckCircle2 size={13} strokeWidth={1.5} />
                <span>Dynamic Entity Sticker Synthesizer (DuckDuckGo + rembg)</span>
              </div>
              <div className="feature-item">
                <CheckCircle2 size={13} strokeWidth={1.5} />
                <span>Meme SFX Audio & Punch-In Zooms (1.25x)</span>
              </div>
            </div>

            <div className="smart-cta-row">
              {autoCutStatus === "success" ? (
                <div className="smart-success-card">
                  <CheckCircle2 size={16} strokeWidth={1.5} />
                  <span>Auto-Cut successfully applied to timeline tracks!</span>
                </div>
              ) : (
                <button
                  type="button"
                  className="smart-trigger-btn"
                  disabled={autoCutStatus === "running" || isProcessingAutoCut}
                  onClick={handleTriggerAutoCut}
                >
                  {autoCutStatus === "running" || isProcessingAutoCut ? (
                    <>
                      <RefreshCw size={15} className="spin-icon" strokeWidth={1.5} />
                      <span>{autoCutPhase || "Running Sarvam AI Director..."}</span>
                    </>
                  ) : (
                    <>
                      <Zap size={15} strokeWidth={1.5} />
                      <span>Execute 1-Click Auto-Cut</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Silence & Cuts */}
      {activeAiTab === "silence" && (
        <div className="smart-ai-content">
          <div className="smart-config-card">
            <h4>Local Silence & Dead-Air Removal</h4>
            <p className="card-desc">
              Detects zero-sound pauses and hesitations locally using pydub at ₹0 API cost.
            </p>
            <div className="smart-config-row">
              <label>Min Silence Duration: {silenceThreshold}s</label>
              <input
                type="range"
                min="0.3"
                max="2.0"
                step="0.1"
                value={silenceThreshold}
                onChange={(e) => setSilenceThreshold(parseFloat(e.target.value))}
                className="smart-slider"
              />
            </div>
            <button
              type="button"
              className="smart-secondary-btn"
              onClick={onApplySilenceCuts}
            >
              <Scissors size={14} strokeWidth={1.25} />
              <span>Scan & Ripple-Cut Dead Air</span>
            </button>
          </div>
        </div>
      )}

      {/* Tab 3: Romanized Captions */}
      {activeAiTab === "captions" && (
        <div className="smart-ai-content">
          <div className="smart-config-card">
            <h4>Phonetic Romanized Indic Subtitles</h4>
            <p className="card-desc">
              Transcribes regional speech into English alphabet transliteration (*"Aaj hum baat karenge..."*) so Gen-Z audiences can read comfortably.
            </p>
            <div className="smart-config-row">
              <label>Caption Style Preset</label>
              <div className="smart-segmented-pills">
                <button type="button" className="pill-btn is-active">
                  TikTok / Reels Yellow Pop
                </button>
                <button type="button" className="pill-btn">
                  Clean Minimal Slate
                </button>
                <button type="button" className="pill-btn">
                  Dual-Color Karaoke
                </button>
              </div>
            </div>
            <button
              type="button"
              className="smart-secondary-btn"
              onClick={onApplyCaptions}
            >
              <Subtitles size={14} strokeWidth={1.25} />
              <span>Generate Romanized Subtitles</span>
            </button>
          </div>
        </div>
      )}

      {/* Tab 4: Dynamic Stickers */}
      {activeAiTab === "stickers" && (
        <div className="smart-ai-content">
          <div className="smart-config-card">
            <h4>Indian Cultural Sticker Synthesizer</h4>
            <p className="card-desc">
              Searches web images for mentioned Indian entities (Zomato, UPI, Biryani, Auto-rickshaw), strips background locally in ~300ms using rembg, and adds transparent sticker overlays to the timeline.
            </p>
            <div className="sticker-sample-grid">
              <div className="sticker-sample-tag">Zomato</div>
              <div className="sticker-sample-tag">Biryani</div>
              <div className="sticker-sample-tag">UPI / GPay</div>
              <div className="sticker-sample-tag">Auto-Rickshaw</div>
              <div className="sticker-sample-tag">Chai / Tea</div>
              <div className="sticker-sample-tag">Cricket</div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 5: Voiceover */}
      {activeAiTab === "voice" && (
        <div className="smart-ai-content">
          <div className="smart-config-card">
            <h4>Indic Speech & Voiceover Synthesis</h4>
            <p className="card-desc">
              Neural Text-to-Speech across 22+ Indic languages and voice cloning.
            </p>
            <div className="smart-config-row">
              <label>Voice Engine</label>
              <div className="smart-segmented-pills">
                <button type="button" className="pill-btn is-active">
                  Kokoro 82M (English/Indic)
                </button>
                <button type="button" className="pill-btn">
                  Piper Indic ONNX
                </button>
                <button type="button" className="pill-btn">
                  Hojo Neural
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 6: AI Music & Audio */}
      {activeAiTab === "music" && (
        <div className="smart-ai-content">
          <div className="smart-config-card">
            <h4>AI Music & Vocal Stem Separation</h4>
            <p className="card-desc">
              Split vocals from background score, isolate dialogue, and generate royalty-free background tracks.
            </p>
            <div className="smart-config-row">
              <label>Music Genre / Vibe</label>
              <div className="smart-segmented-pills">
                <button type="button" className="pill-btn is-active">
                  Lo-Fi Chill
                </button>
                <button type="button" className="pill-btn">
                  Energetic Bollywood Pop
                </button>
                <button type="button" className="pill-btn">
                  Cinematic Ambient
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
