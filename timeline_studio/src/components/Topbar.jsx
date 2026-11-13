import { cancelVideoProxy, clearVideoProxyCache, getVideoProxyMode, getVideoProxyRecord, getVideoProxyRevision, subscribeVideoProxy, setVideoProxyMode } from "../lib/videoProxy.js";
import { useEffect, useLayoutEffect, useRef, useState, useSyncExternalStore } from "react";
import { SplicLogo } from "./SplicLogo.jsx";
import {
  Menu,
  Undo2,
  Redo2,
  ChevronDown,
  Play,
  Pause,
  Settings as SettingsIcon,
  Film,
  Plus,
  FolderOpen,
  Save,
  Upload,
  Download,
  Scissors,
  Copy,
  Trash2,
  Maximize2,
  HelpCircle,
  HardDrive,
  Sliders,
  Database,
  Loader2,
  Link as LinkIcon,
  Unlink,
  ZoomIn,
  ZoomOut,
  Maximize,
  Keyboard,
} from "lucide-react";

import { RATIO_OPTIONS } from "../config/editor.js";
import { LocalProjectNameDialog } from "./LocalProjectNameDialog.jsx";
import { hostText } from "../i18nHost.js";
import { APP_LANGUAGES, saveLanguagePreference } from "../i18n.js";
import { getPrimaryShortcutModifier, releasePointerActivatedFocus } from "../lib/editorShortcuts.js";
import { formatStorageBytes, inspectModelCache } from "../lib/modelCacheInspection.js";
import { ExportSettingsPanel } from "./ExportSettingsPanel.jsx";
import { IconButton, Popover } from "./ui.jsx";

export function Topbar({
  proxySource = "",
  proxyPlaybackSrc = "",
  desktopActions = {},
  hostService = null,
  completeProject = null,
  onOpenProjects = null,
  onOpenSettingsModal = null,
  onOpenNewProjectModal = null,
  projectName = "",
  t,
  compactRail: _compactRail,
  setCompactRail: _setCompactRail,
  lastSaved,
  undo,
  redo,
  ratio,
  ratioId,
  showRatioMenu,
  setShowRatioMenu,
  setRatioId,
  notify,
  isPlaying,
  handlePlayToggle,
  imageSrc,
  exporting,
  handleExportVideo,
  showExportMenu,
  setShowExportMenu,
  exportSettings,
  setExportSettings,
  timelineDuration,
  showSettings,
  setShowSettings,
  activeLanguage,
  setUiLanguage,
  captionsEnabled,
  setCaptionsEnabled,
  trackVisibility,
  toggleTrackVisibility,
  showFileMenu,
  setShowFileMenu: _setShowFileMenu,
  handleNewProject,
  handleExportProject,
  handleImportProject,
  projectFileInputRef,
}) {
  useSyncExternalStore(subscribeVideoProxy, getVideoProxyRevision);
  const proxyMode = getVideoProxyMode();
  const proxyRecord = getVideoProxyRecord(proxySource);
  const proxyPending = ["queued", "preparing"].includes(proxyRecord?.state);
  const [showProxyCache, setShowProxyCache] = useState(false);
  const [clearingProxyCache, setClearingProxyCache] = useState(false);
  const proxyCacheAnchor = useRef(null);
  const [shortcutRequest, setShortcutRequest] = useState(0);
  const fileAnchorRef = useRef(null);
  const fileKeyboardOpen = useRef(false);
  useLayoutEffect(() => {
    if (!showFileMenu || !fileKeyboardOpen.current) return;
    fileAnchorRef.current?.querySelector(".file-menu-action:not(:disabled)")?.focus();
    fileKeyboardOpen.current = false;
  }, [showFileMenu]);
  const shortcutGuideRef = useRef(null);
  const ht = (key) => hostText(activeLanguage, key);
  const [namingProject, setNamingProject] = useState(false);
  const exportAnchorRef = useRef(null);
  const ratioAnchorRef = useRef(null);
  const settingsAnchorRef = useRef(null);
  const modelCacheControlRef = useRef(null);
  const [modelCacheInspection, setModelCacheInspection] = useState({ state: "idle", result: null });
  const shortcutModifier = getPrimaryShortcutModifier();
  const shortcutRows = [
    ["markersAdd", "M"],
    ["markersTitle", "Shift+M"],
    ["shortcutPlayPause", "Space"],
    ["shortcutSplit", `${shortcutModifier}+B`],
    ["shortcutDuplicate", `${shortcutModifier}+D`],
    ["shortcutDelete", "Delete / Backspace"],
    ["shortcutUndo", `${shortcutModifier}+Z`],
    ["shortcutRedo", `${shortcutModifier}+Shift+Z`],
    ["shortcutZoomOut", "−"],
    ["shortcutZoomIn", "+"],
    ["shortcutFitTimeline", "Shift+Z"],
    ["shortcutSelectLeft", "["],
    ["shortcutSelectRight", "]"],
  ];
  const checkModelCache = async () => {
    setModelCacheInspection({ state: "checking", result: null });
    try {
      const result = await inspectModelCache();
      setModelCacheInspection({ state: "ready", result });
    } catch {
      setModelCacheInspection({ state: "unavailable", result: null });
    }
  };
  const modelCacheResult = modelCacheInspection.result;
  const modelCacheSummary = modelCacheResult?.entryCount > 0
    ? t("modelCacheFound")
      .replace("{groups}", String(modelCacheResult.cacheCount))
      .replace("{files}", String(modelCacheResult.entryCount))
    : t("modelCacheEmpty");
  const modelCacheStorage = modelCacheResult?.usage != null
    ? t("modelCacheStorage")
      .replace("{usage}", formatStorageBytes(modelCacheResult.usage))
      .replace("{quota}", modelCacheResult.quota ? formatStorageBytes(modelCacheResult.quota) : "—")
    : "";
  useEffect(() => {
    if (!showSettings || modelCacheInspection.state === "idle") return undefined;
    const frame = window.requestAnimationFrame(() => {
      modelCacheControlRef.current?.scrollIntoView({ block: "nearest" });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [modelCacheInspection.state, showSettings]);

  useLayoutEffect(() => {
    if (showProxyCache) document.querySelector(".proxy-cache-popover .popover-close")?.focus();
  }, [showProxyCache]);
  const closeProxyCache = () => {
    const containedFocus = document.querySelector(".proxy-cache-popover")?.contains(document.activeElement);
    setShowProxyCache(false);
    if (containedFocus) proxyCacheAnchor.current?.parentElement?.querySelector(".is-compact-view [data-editor-menu-trigger]")?.focus();
  };
  const [showUnifiedMenu, setShowUnifiedMenu] = useState(false);
  const [menuTab, setMenuTab] = useState("file");
  const menuAnchorRef = useRef(null);

  const timelineCommand = (command) => window.dispatchEvent(new CustomEvent("editor-timeline-command", { detail: command }));

  const menuIcons = {
    undo: Undo2,
    redo: Redo2,
    desktopDuplicate: Copy,
    desktopDelete: Trash2,
    desktopSelectAll: Copy,
    desktopSplit: Scissors,
    desktopTrim: Scissors,
    desktopSlip: Sliders,
    desktopSlide: Sliders,
    desktopSpeed: Sliders,
    desktopSeparate: Film,
    desktopLink: LinkIcon,
    desktopUnlink: Unlink,
    desktopZoomIn: ZoomIn,
    desktopZoomOut: ZoomOut,
    desktopFit: Maximize2,
    desktopFullscreen: Maximize,
    proxyAuto: HardDrive,
    proxyOriginal: Film,
    proxyCacheManage: HardDrive,
    proxyCancel: Trash2,
    desktopGuide: HelpCircle,
    desktopShortcuts: Keyboard,
    desktopFeedback: HelpCircle,
    desktopAbout: HelpCircle,
  };

  const item = (key, run, disabled = false, shortcut = "") => ({ key, run, disabled, shortcut, icon: menuIcons[key] });
  const proxySourceLabel = proxySource
    ? t("proxyUsing").replace("{source}", t(proxyPlaybackSrc && proxyPlaybackSrc !== proxySource ? "proxyVideo" : "proxyOriginal"))
    : t("proxyNoVideo");

  const menus = [
    {
      id: "edit",
      label: t("desktopEdit", "Edit"),
      items: [
        item("undo", undo, false, `${shortcutModifier}+Z`),
        item("redo", redo, false, `${shortcutModifier}+Shift+Z`),
        null,
        item("desktopDuplicate", desktopActions.duplicate, !desktopActions.hasSelection || desktopActions.selectionLocked, `${shortcutModifier}+D`),
        item("desktopDelete", desktopActions.delete, !desktopActions.hasSelection || desktopActions.selectionLocked, "Delete"),
        item("desktopSelectAll", () => timelineCommand("select-all"), !desktopActions.hasClips),
      ],
    },
    {
      id: "clip",
      label: t("desktopClip", "Clip"),
      items: [
        item("desktopSplit", desktopActions.split, !desktopActions.canSplit, `${shortcutModifier}+B`),
        item("desktopTrim", () => timelineCommand("trim"), !desktopActions.canMainEdit),
        item("desktopSlip", () => timelineCommand("slip"), !desktopActions.canMainEdit),
        item("desktopSlide", () => timelineCommand("slide"), !desktopActions.canMainEdit),
        item("desktopSpeed", desktopActions.speed, !desktopActions.canSpeedEdit),
        null,
        item("desktopSeparate", () => timelineCommand("separate-audio"), !desktopActions.canVideoEdit),
        null,
        item("desktopLink", () => timelineCommand("link-captions"), !desktopActions.canLink),
        item("desktopUnlink", () => timelineCommand("unlink-captions"), !desktopActions.canUnlink),
      ],
    },
    {
      id: "view",
      label: t("desktopView", "View"),
      items: [
        { key: "desktopTimelineGroup", kind: "heading" },
        item("desktopZoomIn", () => timelineCommand("zoom-in"), false, "+"),
        item("desktopZoomOut", () => timelineCommand("zoom-out"), false, "−"),
        item("desktopFit", () => timelineCommand("zoom-fit"), false, "Shift+Z"),
        null,
        { key: "proxyMode", kind: "heading" },
        { ...item("proxyAuto", () => setVideoProxyMode("auto")), checked: proxyMode === "auto" },
        { ...item("proxyOriginal", () => setVideoProxyMode("original")), checked: proxyMode === "original" },
        {
          key: "proxyStatus",
          kind: "status",
          text: proxySourceLabel,
          detail: proxyPending ? `${t("proxyPreparing")} ${Math.round((proxyRecord.progress || 0) * 100)}%` : proxySource && proxyRecord?.state === "ready" ? t("proxyReady") : "",
        },
        ...(proxyPending ? [item("proxyCancel", () => cancelVideoProxy(proxySource))] : []),
        null,
        item("proxyCacheManage", () => setShowProxyCache(true)),
        item("desktopFullscreen", () => window.dispatchEvent(new CustomEvent("editor-preview-command", { detail: "fullscreen" })), !imageSrc),
      ],
    },
    {
      id: "help",
      label: t("desktopHelp", "Help"),
      items: [
        { key: "desktopGuide", icon: HelpCircle, href: "/how-it-works/", external: true },
        item("desktopShortcuts", () => {
          setShowSettings(true);
          setShortcutRequest((value) => value + 1);
        }),
        { key: "desktopFeedback", icon: HelpCircle, href: "https://github.com/MartinDelophy/ai-video-editor/issues", external: true },
        null,
        { key: "desktopAbout", icon: HelpCircle, href: "/features/", external: true },
      ],
    },
  ];

  const renderMenuContent = (tab) => {
    if (tab === "file") {
      return (
        <>
          <button
            type="button"
            className="splic-unified-action-item"
            onClick={() => {
              setShowUnifiedMenu(false);
              if (onOpenNewProjectModal) onOpenNewProjectModal();
              else handleNewProject();
            }}
          >
            <span className="splic-action-left">
              <Plus size={14} strokeWidth={1.5} />
              <span>{t("newProject", "New Project")}</span>
            </span>
          </button>
          {completeProject ? (
            <>
              <button
                type="button"
                className="splic-unified-action-item"
                disabled={completeProject.status === "preparing" || completeProject.status === "saving"}
                onClick={() => {
                  setShowUnifiedMenu(false);
                  void completeProject.open();
                }}
              >
                <span className="splic-action-left">
                  <FolderOpen size={14} strokeWidth={1.5} />
                  <span>{ht("open", "Open Project")}</span>
                </span>
              </button>
              <button
                type="button"
                className="splic-unified-action-item"
                disabled={completeProject.status === "preparing" || completeProject.status === "saving"}
                onClick={() => {
                  setShowUnifiedMenu(false);
                  if (completeProject.projectId) void completeProject.save();
                  else setNamingProject(true);
                }}
              >
                <span className="splic-action-left">
                  <Save size={14} strokeWidth={1.5} />
                  <span>{completeProject.projectId && completeProject.status === "error" ? ht("retry") : ht("save", "Save Project")}</span>
                </span>
                <span className="splic-action-shortcut">{shortcutModifier}+S</span>
              </button>
            </>
          ) : null}
          <div className="splic-action-divider" />
          <button
            type="button"
            className="splic-unified-action-item"
            onClick={() => {
              setShowUnifiedMenu(false);
              desktopActions.importMedia?.();
            }}
          >
            <span className="splic-action-left">
              <Upload size={14} strokeWidth={1.5} />
              <span>{t("desktopImportMedia", "Import Media Files")}</span>
            </span>
          </button>
          <button
            type="button"
            className="splic-unified-action-item"
            onClick={() => {
              setShowUnifiedMenu(false);
              handleImportProject();
            }}
          >
            <span className="splic-action-left">
              <FolderOpen size={14} strokeWidth={1.5} />
              <span>{t("importProject", "Import .timeline Project")}</span>
            </span>
          </button>
          <button
            type="button"
            className="splic-unified-action-item"
            onClick={() => {
              setShowUnifiedMenu(false);
              handleExportProject();
            }}
          >
            <span className="splic-action-left">
              <Download size={14} strokeWidth={1.5} />
              <span>{t("exportProject", "Export .timeline Project")}</span>
            </span>
          </button>
        </>
      );
    }

    const currentMenu = menus.find((m) => m.id === tab);
    if (!currentMenu) return null;

    return (
      <>
        {currentMenu.items.map((it, idx) => {
          if (it === null) return <div key={`sep-${idx}`} className="splic-action-divider" />;
          if (it.kind === "heading") return <div key={it.key} className="splic-action-heading">{t(it.key)}</div>;
          if (it.kind === "note") return <div key={it.key} className="splic-action-note">{t(it.key)}</div>;
          if (it.kind === "status") {
            return (
              <div key={it.key} className="splic-action-status">
                <span>{it.text}</span>
              </div>
            );
          }
          if (it.href) {
            return (
              <a
                key={it.key}
                href={it.href}
                target={it.external ? "_blank" : undefined}
                rel="noreferrer"
                className="splic-unified-action-item"
                onClick={() => setShowUnifiedMenu(false)}
              >
                <span className="splic-action-left">
                  {it.icon ? <it.icon size={14} strokeWidth={1.5} /> : null}
                  <span>{t(it.key)}</span>
                </span>
              </a>
            );
          }

          const IconComponent = it.icon;
          return (
            <button
              key={it.key}
              type="button"
              className="splic-unified-action-item"
              disabled={it.disabled}
              onClick={() => {
                setShowUnifiedMenu(false);
                it.run?.();
              }}
            >
              <span className="splic-action-left">
                {IconComponent ? <IconComponent size={14} strokeWidth={1.5} /> : null}
                <span>{t(it.key)}</span>
              </span>
              {it.shortcut ? <span className="splic-action-shortcut">{it.shortcut}</span> : null}
            </button>
          );
        })}
      </>
    );
  };
  useEffect(() => {
    if (!showSettings || !shortcutRequest) return;
    const frame = requestAnimationFrame(() => { shortcutGuideRef.current?.scrollIntoView({ block: "nearest" }); shortcutGuideRef.current?.focus(); setShortcutRequest(0); });
    return () => cancelAnimationFrame(frame);
  }, [showSettings, shortcutRequest]);
  useEffect(() => {
    const query = window.matchMedia("(min-width: 1280px)");
    const resized = () => { if (!query.matches) setShowUnifiedMenu(false); };
    query.addEventListener("change", resized);
    return () => query.removeEventListener("change", resized);
  }, []);

  return (
    <header className="topbar">
      {namingProject && completeProject ? (
        <LocalProjectNameDialog
          language={activeLanguage}
          onClose={() => setNamingProject(false)}
          onSave={(name) => {
            setNamingProject(false);
            void completeProject.save(name);
          }}
        />
      ) : null}

      <div className="project-cluster">
        {onOpenProjects && (
          <button
            type="button"
            onClick={onOpenProjects}
            style={{
              background: "none",
              border: "none",
              padding: "2px 6px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
            title="Return to Projects Dashboard"
          >
            <SplicLogo size={20} showText={false} />
            <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--splic-text-muted)", letterSpacing: "0.05em" }}>
              PROJECTS /
            </span>
          </button>
        )}

        <div className="splic-topbar-title-block">
          <div className="project-title" title={projectName || completeProject?.name || t("projectTitle")}>
            {projectName || completeProject?.name || t("projectTitle")}
          </div>

          <div
            className="splic-autosave-status"
            title={completeProject?.error || undefined}
            role={completeProject ? "status" : undefined}
          >
            <span className="splic-autosave-dot" />
            <span>
              {completeProject?.status === "saving" ? "Saving..." : completeProject?.lastSaved ? "Saved" : lastSaved ? "Saved" : "Autosaved"}
            </span>
          </div>
        </div>

        {/* Unified Clean Menu Dropdown (Consolidates File, Edit, Clip, View, Help) */}
        <div className="menu-anchor" ref={menuAnchorRef}>
          <button
            className="splic-unified-menu-btn"
            type="button"
            aria-expanded={showUnifiedMenu}
            onClick={() => setShowUnifiedMenu((open) => !open)}
            title="Editor Menu (File, Edit, Clip, View, Help)"
          >
            <Menu size={14} strokeWidth={1.5} />
            <span>Menu</span>
            <ChevronDown size={11} strokeWidth={1.75} />
          </button>
          {showUnifiedMenu ? (
            <Popover anchorRef={menuAnchorRef} closeLabel={t("close")} onClose={() => setShowUnifiedMenu(false)}>
              <div className="splic-unified-menu-card">
                <div className="splic-unified-tabs">
                  {[
                    { id: "file", label: t("fileMenu", "File") },
                    { id: "edit", label: t("desktopEdit", "Edit") },
                    { id: "clip", label: t("desktopClip", "Clip") },
                    { id: "view", label: t("desktopView", "View") },
                    { id: "help", label: t("desktopHelp", "Help") },
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      type="button"
                      className={`splic-unified-tab ${menuTab === tab.id ? "is-active" : ""}`}
                      onClick={() => setMenuTab(tab.id)}
                      onMouseEnter={() => setMenuTab(tab.id)}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
                <div className="splic-unified-content">
                  {renderMenuContent(menuTab)}
                </div>
              </div>
            </Popover>
          ) : null}
          <input
            ref={projectFileInputRef}
            className="project-file-input"
            type="file"
            accept="application/zip,.timeline"
            onChange={(event) => event.target.files?.[0] && handleImportProject(event.target.files[0])}
          />
        </div>

        {/* Proxy Cache Dialog Anchor */}
        <div className="menu-anchor" ref={proxyCacheAnchor}>
          {showProxyCache ? (
            <Popover portal anchorRef={proxyCacheAnchor} className="proxy-cache-popover" closeLabel={t("close")} onClose={closeProxyCache}>
              <section className="proxy-cache-panel" aria-label={t("proxyCacheManage")}>
                <h3><HardDrive size={18} strokeWidth={1.25} />{t("proxyCacheManage")}</h3>
                <p>{t("proxyCacheDescription")}</p>
                <button
                  type="button"
                  className="panel-secondary"
                  disabled={clearingProxyCache}
                  onClick={async () => {
                    setClearingProxyCache(true);
                    try {
                      await clearVideoProxyCache();
                      closeProxyCache();
                    } finally {
                      setClearingProxyCache(false);
                    }
                  }}
                >
                  <Trash2 size={15} strokeWidth={1.25} />
                  {t("proxyClear")}
                </button>
              </section>
            </Popover>
          ) : null}
        </div>
      </div>

      <div className="topbar-center">
        <button
          className="splic-topbar-tool-btn"
          type="button"
          title={`${t("undo")} (${shortcutModifier}+Z)`}
          onClick={(event) => {
            undo();
            releasePointerActivatedFocus(event);
          }}
        >
          <Undo2 size={15} strokeWidth={1.5} />
          <span>{t("undo")}</span>
        </button>
        <button
          className="splic-topbar-tool-btn"
          type="button"
          title={`${t("redo")} (${shortcutModifier}+Shift+Z)`}
          onClick={(event) => {
            redo();
            releasePointerActivatedFocus(event);
          }}
        >
          <Redo2 size={15} strokeWidth={1.5} />
          <span>{t("redo")}</span>
        </button>
        <span className="divider" />
        <div className="menu-anchor" ref={ratioAnchorRef}>
          <button
            className="ratio-select"
            type="button"
            onClick={() => setShowRatioMenu((open) => !open)}
          >
            {ratio.label} <ChevronDown size={13} strokeWidth={1.5} />
          </button>
          {showRatioMenu ? (
            <Popover anchorRef={ratioAnchorRef} closeLabel={t("close")} showClose={false} onClose={() => setShowRatioMenu(false)}>
              <div className="menu-list">
                {RATIO_OPTIONS.map((option) => (
                  <button
                    type="button"
                    className={option.id === ratioId ? "is-selected" : ""}
                    key={option.id}
                    onClick={() => {
                      setRatioId(option.id);
                      setShowRatioMenu(false);
                      notify(`Canvas aspect ratio switched to ${option.label}`);
                    }}
                  >
                    {option.label}
                    <span>
                      {option.width} x {option.height}
                    </span>
                  </button>
                ))}
              </div>
            </Popover>
          ) : null}
        </div>
      </div>

      <div className="topbar-actions">
        {hostService}
        {/* SOCIAL LINKS REMOVED AS REQUESTED */}
        <button
          className="preview-button"
          type="button"
          title={`${t("shortcutPlayPause")} · Space`}
          onClick={(event) => {
            handlePlayToggle();
            releasePointerActivatedFocus(event);
          }}
        >
          {isPlaying ? <Pause size={15} strokeWidth={1.5} /> : <Play size={15} strokeWidth={1.5} />}
          <span>{t("preview")}</span>
        </button>
        <div className="menu-anchor" ref={exportAnchorRef}>
          <button
            className="export-button"
            type="button"
            aria-expanded={showExportMenu}
            disabled={exporting}
            onClick={() => setShowExportMenu((open) => !open)}
          >
            <Film size={15} strokeWidth={1.5} />
            <span className="export-button-label">
              {exporting ? t("exporting") : t(exportSettings.mediaType === "audio" ? "audioExportTitle" : "exportVideo")}
            </span>
            {!exporting ? <ChevronDown size={12} strokeWidth={1.75} /> : null}
          </button>
          {showExportMenu ? (
            <Popover anchorRef={exportAnchorRef} className="export-settings-popover" closeLabel={t("close")} onClose={() => setShowExportMenu(false)}>
              <ExportSettingsPanel
                t={t}
                ratio={ratio}
                imageSrc={imageSrc}
                timelineDuration={timelineDuration}
                exportSettings={exportSettings}
                setExportSettings={setExportSettings}
                handleExportVideo={handleExportVideo}
                onClose={() => setShowExportMenu(false)}
              />
            </Popover>
          ) : null}
        </div>
        <div className="menu-anchor" ref={settingsAnchorRef}>
          <IconButton
            label={t("settings")}
            active={showSettings}
            onClick={() => {
              if (onOpenSettingsModal) onOpenSettingsModal();
              else setShowSettings((open) => !open);
            }}
          >
            <SettingsIcon size={17} strokeWidth={1.25} />
          </IconButton>
          {showSettings ? (
            <Popover anchorRef={settingsAnchorRef} closeLabel={t("close")} onClose={() => setShowSettings(false)}>
              <div className="settings-panel">
                <strong>{t("exportSettings")}</strong>
                <label>
                  <span>{t("language")}</span>
                  <select
                    value={activeLanguage}
                    onChange={(event) => {
                      const nextLanguage = event.target.value;
                      saveLanguagePreference(nextLanguage);
                      setUiLanguage(nextLanguage);
                    }}
                  >
                    {APP_LANGUAGES.map((language) => (
                      <option value={language.id} key={language.id}>
                        {language.nativeName}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={captionsEnabled}
                    onChange={(event) => setCaptionsEnabled(event.target.checked)}
                  />
                  {t("exportCaptions")}
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={trackVisibility.audio}
                    onChange={() => toggleTrackVisibility("audio")}
                  />
                  {t("enableAudioTrack")}
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={trackVisibility.source}
                    onChange={() => toggleTrackVisibility("source")}
                  />
                  {t("enableSourceTrack")}
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={trackVisibility.music}
                    onChange={() => toggleTrackVisibility("music")}
                  />
                  {t("enableMusicTrack")}
                </label>
                <section ref={shortcutGuideRef} tabIndex={-1} className="shortcut-guide" aria-labelledby="shortcut-guide-title">
                  <div className="shortcut-guide-heading">
                    <strong id="shortcut-guide-title">{t("keyboardShortcuts")}</strong>
                    <span>Splic Studio</span>
                  </div>
                  <p>{t("keyboardShortcutsHint")}</p>
                  <dl>
                    {shortcutRows.map(([labelKey, shortcut]) => (
                      <div key={labelKey}>
                        <dt>{t(labelKey)}</dt>
                        <dd><kbd>{shortcut}</kbd></dd>
                      </div>
                    ))}
                  </dl>
                </section>
                <div ref={modelCacheControlRef} className="model-cache-control">
                  {modelCacheInspection.state !== "idle" ? (
                    <div className={`model-cache-result is-${modelCacheInspection.state}`} role="status" aria-live="polite">
                      <strong>{modelCacheInspection.state === "checking"
                        ? t("modelCacheChecking")
                        : modelCacheInspection.state === "unavailable"
                          ? t("modelCacheUnavailable")
                          : modelCacheSummary}</strong>
                      {modelCacheInspection.state === "ready" && modelCacheStorage ? <span>{modelCacheStorage}</span> : null}
                    </div>
                  ) : null}
                  <button type="button" disabled={modelCacheInspection.state === "checking"} onClick={checkModelCache}>
                    <span>{modelCacheInspection.state === "checking" ? t("modelCacheChecking") : t("checkModelCache")}</span>
                    {modelCacheInspection.state === "checking" ? <Loader2 className="is-spinning" size={15} strokeWidth={1.5} /> : <Database size={15} strokeWidth={1.5} />}
                  </button>
                </div>
              </div>
            </Popover>
          ) : null}
        </div>
      </div>
    </header>
  );
}
