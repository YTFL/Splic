import React, { useState, useRef } from "react";
import {
  Wand2,
  Upload,
  AlertCircle,
  FileText,
  X,
  Scissors,
  Music,
  Smile,
  Play,
} from "lucide-react";
import { normalizeEditPlan, SAMPLE_EDIT_PLAN } from "../lib/editPlanEngine.js";

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
  userAssets = [],
}) {
  const fileInputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleClose = () => {
    setError(null);
    setLoading(false);
    onClose?.();
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
        const parsed = JSON.parse(text);
        // Validate with schema normalizer
        normalizeEditPlan(parsed, userAssets);
        setLoading(false);
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

  const handleLoadSample = () => {
    handleClose();
    onStartAutoEdit?.(SAMPLE_EDIT_PLAN);
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
              <h2 className="splic-modal-title">⚡ Auto Edit — Upload JSON Instructions</h2>
              <p className="splic-modal-sub">
                Upload your Sarvam AI EditPlan JSON to watch the agentic pipeline cut and assemble tracks in real-time
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
            onClick={() => fileInputRef.current?.click()}
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
                {loading ? "Validating Edit Plan..." : "Click to browse or drop EditPlan .json file"}
              </span>
              <p style={{ margin: "4px 0 0", fontSize: "11px", color: "var(--splic-text-muted)" }}>
                Reads JSON instructions and plays real-time animations tailored to the edit plan
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
            onClick={handleLoadSample}
            title="Load sample Hinglish tech reel edit plan"
          >
            <Play size={13} strokeWidth={2} style={{ color: "var(--splic-red-primary)" }} />
            <span>Load Sample Edit Plan</span>
          </button>

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
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
