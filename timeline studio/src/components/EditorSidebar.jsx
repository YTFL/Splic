import React from "react";
import {
  Folder,
  Wand2,
  Sparkles,
  Music,
  Layout,
  Smile,
  Zap,
} from "lucide-react";
import { COMPACT_WORKSPACE_QUERY } from "../config/editor.js";
import { SPECIAL_EFFECTS_LABELS } from "../i18nEffectClips.js";
import { TimelineEffectCatalog } from "./TimelineEffects.jsx";
import { templateCopy } from "../i18nTemplates.js";
import { TemplateLibrary } from "./TemplateLibrary.jsx";
import { createEffectClip } from "../lib/timelineEffects.js";
import { MediaPanel, ToolPanel } from "./panels.jsx";
import { PluginCatalogPanel } from "./GenerationPlugins.jsx";
import { SmartAiWorkspace } from "./SmartAiWorkspace.jsx";

export function EditorSidebar({ model: d, workspaceMode = "editor" }) {
  const toolLabel = (id, fallback) => {
    if (id === "specialEffects") return SPECIAL_EFFECTS_LABELS[d.activeLanguage] || SPECIAL_EFFECTS_LABELS.en;
    if (id === "templates") return templateCopy(d.activeLanguage).title;
    return d.t(id, fallback || id);
  };

  // Nuances tabs for the Editor screen (DaVinci Resolve side inspector / media pool)
  const editorNuanceTabs = [
    { id: "media", label: "Media Pool", icon: Folder },
    { id: "effects", label: "Visual Effects", icon: Wand2 },
    { id: "specialEffects", label: "Special Effects", icon: Sparkles },
    { id: "audio", label: "Audio Effects", icon: Music },
    { id: "templates", label: "Templates", icon: Layout },
    { id: "stickers", label: "Stickers", icon: Smile },
  ];

  const activeNuanceId = d.activeTool === "smart" || d.activeTool === "caption" ? "media" : d.activeTool;

  return (
    <aside className={`davinci-editor-sidebar ${d.compactRail ? "is-compact" : ""}`}>
      {/* If on Smart / AI workspace page, show the dedicated Smart AI Studio */}
      {workspaceMode === "smart" ? (
        <div className="davinci-side-pane smart-pane-mode">
          <header className="davinci-side-pane-header">
            <div className="davinci-pane-title-group">
              <Zap size={16} strokeWidth={1.5} className="davinci-accent-icon" />
              <h3 className="davinci-pane-title">Smart / AI Studio</h3>
            </div>
            <span className="davinci-pill-badge">Sarvam AI Powered</span>
          </header>
          <div className="davinci-pane-body">
            <SmartAiWorkspace
              autoEdit={d.autoEdit}
              silenceRemoval={d.silenceRemoval}
              aiMusic={d.aiMusic}
              activeLanguage={d.activeLanguage}
              t={d.t}
              hasVisual={Boolean(d.previewVisualSrc)}
              onApplyCaptions={() => {
                d.selectTool("caption");
                if (d.generateCaptionsFromSourceAudio) d.generateCaptionsFromSourceAudio();
              }}
              onApplySilenceCuts={() => {
                if (d.silenceRemoval?.detectAndCut) d.silenceRemoval.detectAndCut();
              }}
            />
          </div>
        </div>
      ) : (
        /* Standard Editor Workspace: Nuances Side Panel (Media, Effects, Audio, Templates, etc.) */
        <div className="davinci-side-pane editor-nuances-mode">
          {/* Top Nuances Tab Bar (DaVinci Resolve Inspector/Pool style) */}
          <nav className="davinci-nuances-nav" role="tablist" aria-label="Editor Nuances">
            {editorNuanceTabs.map(({ id, label, icon: Icon }) => {
              const isActive = (d.activeTool === id) || (activeNuanceId === id && !["media", "effects", "specialEffects", "audio", "templates", "stickers"].includes(d.activeTool) && id === "media");
              return (
                <button
                  key={id}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  className={`davinci-nuance-btn ${isActive ? "is-active" : ""}`}
                  onClick={() => {
                    d.selectTool(id);
                    if (window.matchMedia?.(COMPACT_WORKSPACE_QUERY).matches) {
                      d.setMobilePanel?.("tools");
                    }
                  }}
                  title={label}
                >
                  <Icon size={14} strokeWidth={isActive ? 1.75 : 1.25} />
                  <span>{label}</span>
                </button>
              );
            })}
          </nav>

          {/* Active Nuance Panel Content */}
          <div className="davinci-pane-body">
            {d.activeTool === "media" ? (
              <MediaPanel
                t={d.t}
                mediaTab={d.mediaTab}
                setMediaTab={d.setMediaTab}
                isDragging={d.isDragging}
                setIsDragging={d.setIsDragging}
                fileInputRef={d.fileInputRef}
                handleFiles={d.handleFiles}
                imageSrc={d.imageSrc}
                builtInAssets={d.builtInAssets}
                libraryType={d.libraryType}
                libraryQuery={d.libraryQuery}
                setLibraryQuery={d.setLibraryQuery}
                selectLibraryType={d.selectLibraryType}
                libraryStatus={d.libraryStatus}
                libraryError={d.libraryError}
                libraryProvider={d.libraryProvider}
                assetDownloadStates={d.assetDownloadStates}
                prefetchLibraryAsset={d.prefetchLibraryAsset}
                userAssets={d.userAssets}
                selectedLibraryAssetId={d.selectedLibraryAssetId}
                deleteUserAsset={d.deleteUserAsset}
                draggedAssetId={d.draggedAssetId}
                handleAssetPointerDown={d.handleAssetPointerDown}
                handleAssetClick={d.handleAssetClick}
                applyAssetToTrack={d.applyAssetToTrack}
                closeMobilePanel={() => d.setMobilePanel?.("")}
                mobilePanelOpen={d.mobilePanel === "tools"}
                soundAddDisabled={d.trackLocks.audio || d.trackVisibility.audio === false}
                isPlaying={d.isPlaying}
                pauseForTimelineEdit={d.pauseForTimelineEdit}
                language={d.activeLanguage}
                onGeneratedVector={d.handleGeneratedVector}
                onOpenAiMusic={() => {
                  d.setSmartMode("ai-music");
                  d.selectTool("audio");
                }}
              />
            ) : d.activeTool === "specialEffects" ? (
              <TimelineEffectCatalog
                selectedEffect={d.effectClips?.find((clip) => clip.id === d.selectedEffectClipId)?.effect}
                language={d.activeLanguage}
                onAdd={(effect) => {
                  if (d.trackLocks?.effects) return;
                  const clip = createEffectClip(effect, d.currentTime);
                  d.setEffectClips?.((items) => [...items, clip]);
                  d.setSelectedEffectClipId?.(clip.id);
                  d.setSelectedTrack?.("effects");
                  d.setMobilePanel?.("inspector");
                }}
              />
            ) : d.activeTool === "templates" ? (
              <TemplateLibrary
                language={d.activeLanguage}
                selected={d.selectedTemplateId}
                onSelect={d.selectTemplate}
              />
            ) : d.activeTool === "plugins" ? (
              <PluginCatalogPanel
                language={d.activeLanguage}
                plugins={d.generationPlugins}
                onOpenInspector={d.showPluginInspector}
              />
            ) : (
              <ToolPanel
                activeTool={d.activeTool}
                uiLanguage={d.activeLanguage}
                script={d.script}
                updateScript={d.updateScript}
                segments={d.segments}
                currentSegmentIndex={d.currentSegmentIndex}
                captionSegments={d.captionSegments}
                captionTargetDuration={d.captionTargetDuration}
                selectedCaptionSegment={d.selectedCaptionSegment}
                selectedSegmentId={d.selectedSegmentId}
                setSelectedSegmentId={d.setSelectedSegmentId}
                updateCaptionSegmentText={d.updateCaptionSegmentText}
                toggleCaptionSegmentHidden={d.toggleCaptionSegmentHidden}
                deleteCaptionSegment={d.deleteCaptionSegment}
                seekTo={d.seekTo}
                estimatedDuration={d.estimatedDuration}
                captionPosition={d.captionPosition}
                setCaptionPosition={d.handleCaptionPositionChange}
                syncCaptionPositions={d.syncCaptionPositions}
                captionSize={d.captionSize}
                setCaptionSize={d.setCaptionSize}
                captionStyle={d.captionStyle}
                setCaptionStyle={d.setCaptionStyle}
                captionStylePresetId={d.captionStylePresetId}
                setCaptionStylePresetId={d.setCaptionStylePresetId}
                captionStylePresets={d.captionStylePresets}
                setCaptionStylePresets={d.setCaptionStylePresets}
                setCaptionSegments={d.setCaptionSegments}
                captionsEnabled={d.captionsEnabled}
                setCaptionsEnabled={d.setCaptionsEnabled}
                selectedFilterId={d.selectedFilterId}
                setSelectedFilterId={d.setSelectedFilterId}
                selectedTransitionId={d.selectedTransitionId}
                setSelectedTransitionId={d.setSelectedTransitionId}
                selectedStickerId={d.selectedStickerId}
                setSelectedStickerId={d.setSelectedStickerId}
                handleStickerPointerDown={d.handleAssetPointerDown}
                handleStickerClick={d.handleStickerClick}
                confirmStickerSelection={d.confirmStickerSelection}
                closeMobilePanel={() => d.setMobilePanel?.("")}
                mobilePanelOpen={d.mobilePanel === "tools"}
                audioBlob={d.audioBlob}
                audioDuration={d.audioDuration}
                sourceAudioBlob={d.sourceAudioBlob}
                sourceAudioName={d.sourceAudioName}
                sourceAudioDuration={d.sourceAudioDuration}
                clearSourceAudioTrack={d.clearSourceAudioTrack}
                generateCaptionsFromSourceAudio={d.generateCaptionsFromSourceAudio}
                isGeneratingCaptions={d.status === "captioning"}
                automaticCaptionProgress={d.status === "captioning" ? d.progress : 0}
                selectedAudioToolTarget={d.selectedAudioToolTarget}
                audioWorkspace={d.audioWorkspace}
                vocalSeparationJob={d.vocalSeparationJob}
                hasVisual={Boolean(d.previewVisualSrc)}
                visualType={d.previewVisualType}
                smartFrame={d.smartFrame}
                analyzeCurrentVisual={d.analyzeCurrentVisual}
                analyzeEffectVisual={d.analyzeEffectVisual}
                openAvatarPanel={d.openAvatarPanel}
                activeLanguage={d.activeLanguage}
                t={d.t}
                trOption={d.trOption}
                notify={d.notify}
              />
            )}
          </div>
        </div>
      )}
    </aside>
  );
}
