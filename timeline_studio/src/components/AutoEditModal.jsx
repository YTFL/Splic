import { useCallback, useEffect, useRef, useState } from "react";
import {
  Wand2,
  Upload,
  AlertCircle,
  FileText,
  X,
  Scissors,
  Music,
  Smile,
  Zap,
  Loader2,
  Film,
  CheckCircle2,
} from "lucide-react";
import { normalizeEditPlan } from "../lib/editPlanEngine.js";
import { AUTO_CUT_LIVE_STATUS, extractEditPlan, isBackendEditPlan } from "../lib/autoCut.js";

const PHASE_LABELS = AUTO_CUT_LIVE_STATUS;

/**
 * AutoEditModal:
 * Clean, production-grade JSON instruction uploader.
 * Once a valid JSON file is dropped, browsed, or sample selected, it triggers
 * the full AutoEditEngine to play the agentic animations and edit the timeline.
 */
export function AutoEditModal({
  isOpen = false,
  onClose,
  onStartAutoEdit,
  onRunAutoCut,
  targetClipName = "",
  autoStart = false,
  onAutoStartConsumed,
  userAssets = [],
}) {
  const fileInputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [phase, setPhase] = useState("");
  const [summary, setSummary] = useState(null);
  const runRef = useRef(null);

  // Opening Auto Edit from an editor button starts the backend run immediately.
  useEffect(() => {
    if (!isOpen || !autoStart) return;
    onAutoStartConsumed?.();
    if (targetClipName) runRef.current?.();
  }, [isOpen, autoStart, targetClipName, onAutoStartConsumed]);

  const handleClose = useCallback(() => {
    setError(null);
    setLoading(false);
    setSummary(null);
    setPhase("");
    onClose?.();
  }, [onClose]);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === "Escape") handleClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, handleClose]);

  if (!isOpen) return null;

  const running = Boolean(phase);

  const runAutoCut = async (plan = null) => {
    if (running || !onRunAutoCut) return;
    setError(null);
    setSummary(null);
    setPhase("uploading");
    try {
      setSummary(await onRunAutoCut({ plan, onPhase: setPhase }));
    } catch (err) {
      setError(err?.message || "Auto-Cut failed");
    } finally {
      setPhase("");
    }
  };

  const processFile = (file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".json")) {
      setError("Please upload a valid .json file containing Sarvam AI edit instructions");
      return;
    }

    setLoading(true);
    setError(null);

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const text = e.target?.result;
        const raw = JSON.parse(typeof text === "string" ? text.trim() : text);
        const parsed = extractEditPlan(raw);
        setLoading(false);
        if (!parsed) {
          const keys = raw && typeof raw === "object" ? Object.keys(raw).slice(0, 8).join(", ") : typeof raw;
          setError(`"${file.name}" is not an EditPlan: expected cuts / captions / stickers / sfx, found: ${keys || "nothing"}`);
          return;
        }
        if (isBackendEditPlan(parsed)) {
          void runAutoCut(parsed);
          return;
        }
        // Legacy demo JSON: validate with schema normalizer and play the animated demo
        normalizeEditPlan(parsed, userAssets);
        handleClose();
        onStartAutoEdit?.(parsed);
      } catch (err) {
        setLoading(false);
        setError(err.message || "Incompatible JSON instructions file");
      }
    };
    reader.onerror = () => {
      setLoading(false);
      setError("Failed to read the selected file");
    };
    reader.readAsText(file);
  };

  runRef.current = () => runAutoCut();

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  };

  return (
    <div className="splic-modal-backdrop" onClick={handleClose}>
      <div
        className="splic-modal-card"
        style={{ maxWidth: "560px", width: "92%" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="splic-modal-header">
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "8px",
                background: "rgba(229, 57, 53, 0.12)",
                border: "1px solid rgba(229, 57, 53, 0.25)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--splic-red-primary)",
              }}
            >
              <Wand2 size={18} strokeWidth={1.5} />
            </div>
            <div>
              <h2 className="splic-modal-title">Auto-Cut</h2>
              <p className="splic-modal-sub">
                Send your timeline video to the Sarvam AI pipeline, or load an EditPlan JSON, to get editable cuts, captions, stickers and SFX
              </p>
            </div>
          </div>

          <button
            type="button"
            className="splic-modal-close"
            onClick={handleClose}
            aria-label="Close"
          >
            <X size={16} strokeWidth={1.5} />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: "20px 24px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "12px",
              padding: "14px 16px",
              borderRadius: "10px",
              background: "var(--splic-bg-card)",
              border: "1px solid var(--splic-border-subtle)",
              marginBottom: "16px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px", minWidth: 0 }}>
              <Film size={18} strokeWidth={1.25} style={{ color: "var(--splic-text-muted)", flexShrink: 0 }} />
              <div style={{ minWidth: 0 }}>
                <div
                  style={{
                    fontSize: "12.5px",
                    fontWeight: 700,
                    color: "var(--splic-text-bright)",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {targetClipName || "No video on the timeline"}
                </div>
                <div style={{ fontSize: "11px", color: "var(--splic-text-muted)", marginTop: "2px" }}>
                  {running
                    ? PHASE_LABELS[phase] || "Working..."
                    : targetClipName
                      ? "Analyzes the selected (or first) video clip with Sarvam AI"
                      : "Import a video onto the timeline to enable Auto-Cut"}
                </div>
              </div>
            </div>
            <button
              type="button"
              className="splic-btn-primary"
              style={{ width: "auto", height: "34px", minHeight: "34px", padding: "0 14px", fontSize: "12.5px", flexShrink: 0 }}
              disabled={!targetClipName || running || !onRunAutoCut}
              onClick={() => void runAutoCut()}
            >
              {running
                ? <Loader2 size={14} strokeWidth={1.5} style={{ animation: "auto-edit-spin 0.9s linear infinite" }} />
                : <Zap size={14} strokeWidth={1.5} />}
              <span>{running ? "Running..." : "Run Auto-Cut"}</span>
            </button>
          </div>

          {summary && (
            <div
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "8px",
                padding: "10px 14px",
                borderRadius: "8px",
                background: "rgba(34, 197, 94, 0.1)",
                border: "1px solid rgba(34, 197, 94, 0.28)",
                color: "#4ade80",
                fontSize: "12px",
                marginBottom: "16px",
              }}
            >
              <CheckCircle2 size={16} strokeWidth={1.5} style={{ flexShrink: 0 }} />
              <div>
                <div>
                  Applied {summary.cuts} cuts, {summary.captions} captions, {summary.stickers} stickers and {summary.sfx} SFX
                  {summary.director ? ` (director: ${summary.director})` : ""}. Every item is editable on the timeline.
                </div>
                {summary.warnings?.map((warning) => (
                  <div key={warning} style={{ color: "#fbbf24", marginTop: "4px" }}>{warning}</div>
                ))}
              </div>
            </div>
          )}

          {error && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "10px 14px",
                borderRadius: "8px",
                background: "rgba(239, 68, 68, 0.12)",
                border: "1px solid rgba(239, 68, 68, 0.28)",
                color: "#f87171",
                fontSize: "12px",
                marginBottom: "16px",
              }}
            >
              <AlertCircle size={16} strokeWidth={1.5} />
              <span>{error}</span>
            </div>
          )}

          {/* Drag & Drop Zone */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => { if (!running) fileInputRef.current?.click(); }}
            style={{
              border: dragOver
                ? "2px dashed var(--splic-red-primary)"
                : "1.5px dashed var(--splic-border-strong)",
              borderRadius: "10px",
              padding: "34px 20px",
              textAlign: "center",
              background: dragOver ? "rgba(229, 57, 53, 0.05)" : "var(--splic-bg-surface)",
              cursor: "pointer",
              transition: "all 0.18s ease",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: "10px",
            }}
          >
            <input
              type="file"
              ref={fileInputRef}
              accept=".json,application/json"
              style={{ display: "none" }}
              onChange={handleFileChange}
            />

            <div
              style={{
                width: "48px",
                height: "48px",
                borderRadius: "10px",
                background: "var(--splic-bg-card)",
                border: "1px solid var(--splic-border-subtle)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--splic-text-muted)",
              }}
            >
              <Upload size={22} strokeWidth={1.5} />
            </div>

            <div>
              <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--splic-text-bright)" }}>
                {loading ? "Validating Edit Plan..." : "Or browse / drop an EditPlan .json file"}
              </span>
              <p style={{ margin: "4px 0 0", fontSize: "11px", color: "var(--splic-text-muted)" }}>
                Backend EditPlans are applied to your timeline video; legacy demo plans play the animated demo
              </p>
            </div>
          </div>

          {/* Supported Directive Pills */}
          <div style={{ marginTop: "18px" }}>
            <span
              style={{
                fontSize: "11px",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.5px",
                color: "var(--splic-text-muted)",
                display: "block",
                marginBottom: "8px",
              }}
            >
              Compatible Sarvam AI JSON Directives
            </span>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "7px",
                  padding: "8px 10px",
                  background: "var(--splic-bg-card)",
                  borderRadius: "6px",
                  border: "1px solid var(--splic-border-subtle)",
                  fontSize: "11px",
                  color: "var(--splic-text-bright)",
                }}
              >
                <Scissors size={13} strokeWidth={1.5} style={{ color: "var(--splic-red-primary)" }} />
                <span>Dead-Air Ripple Cuts</span>
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "7px",
                  padding: "8px 10px",
                  background: "var(--splic-bg-card)",
                  borderRadius: "6px",
                  border: "1px solid var(--splic-border-subtle)",
                  fontSize: "11px",
                  color: "var(--splic-text-bright)",
                }}
              >
                <FileText size={13} strokeWidth={1.5} style={{ color: "var(--splic-red-primary)" }} />
                <span>Romanized Indic Subtitles</span>
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "7px",
                  padding: "8px 10px",
                  background: "var(--splic-bg-card)",
                  borderRadius: "6px",
                  border: "1px solid var(--splic-border-subtle)",
                  fontSize: "11px",
                  color: "var(--splic-text-bright)",
                }}
              >
                <Smile size={13} strokeWidth={1.5} style={{ color: "var(--splic-red-primary)" }} />
                <span>Dynamic Cultural Stickers</span>
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "7px",
                  padding: "8px 10px",
                  background: "var(--splic-bg-card)",
                  borderRadius: "6px",
                  border: "1px solid var(--splic-border-subtle)",
                  fontSize: "11px",
                  color: "var(--splic-red-primary)",
                }}
              >
                <Music size={13} strokeWidth={1.5} style={{ color: "var(--splic-red-primary)" }} />
                <span>Contextual Meme SFX</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div
          className="splic-modal-actions"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "16px 24px",
            borderTop: "1px solid var(--splic-border-subtle)",
            background: "var(--splic-bg-surface)",
          }}
        >
          <span />
          <button
            type="button"
            className="splic-btn-secondary"
            style={{
              width: "auto",
              height: "34px",
              minHeight: "34px",
              maxHeight: "34px",
              borderRadius: "8px",
              padding: "0 14px",
              fontSize: "12.5px",
              fontWeight: 600,
            }}
            onClick={handleClose}
            disabled={running}
          >
            {summary ? "Done" : "Cancel"}
          </button>
        </div>
      </div>
    </div>
  );
}
