import React, { useState } from "react";
import {
  Plus,
  Search,
  Sliders,
  Clock,
  Film,
  Sparkles,
  MoreVertical,
  Layers,
  ArrowRight,
  Trash2,
  Copy,
  ExternalLink,
  Settings,
  User,
  LogOut,
  RefreshCw,
  Loader2,
  AlertCircle,
  X,
} from "lucide-react";
import { SplicLogo } from "./SplicLogo.jsx";
import { getStoragePaths } from "../lib/projectsApi.js";

const STATUS_LABELS = { draft: "Draft", auto_edited: "Auto-edited", in_progress: "In progress", ready_for_export: "Ready to export" };

function projectCountsLine(project) {
  const c = project.counts || {};
  return [
    c.captions ? `${c.captions} captions` : "",
    c.stickers ? `${c.stickers} stickers` : "",
    c.cuts ? `${c.cuts} cuts` : "",
    c.sfx ? `${c.sfx} SFX` : "",
  ].filter(Boolean).join(" · ");
}

export function ProjectsDashboard({
  projects = [],
  onOpenProject,
  onNewProject,
  onOpenSettings,
  onOpenSplash,
  onDeleteProject,
  projectsStatus = { state: "ready", error: "" },
  onRetryProjects,
  user,
  onLogout,
}) {
  const [searchQuery, setSearchQuery] = useState("");
  // Two-step delete: the first click arms the card, the second deletes it.
  const [confirmDeleteId, setConfirmDeleteId] = useState("");
  const [deletingId, setDeletingId] = useState("");
  const requestDelete = async (event, project) => {
    event.stopPropagation();
    if (!onDeleteProject || deletingId) return;
    if (confirmDeleteId !== project.id) {
      setConfirmDeleteId(project.id);
      return;
    }
    setDeletingId(project.id);
    try {
      await onDeleteProject(project.id);
    } finally {
      setDeletingId("");
      setConfirmDeleteId("");
    }
  };
  const cancelDelete = (event) => {
    event.stopPropagation();
    setConfirmDeleteId("");
  };
  const [filterRatio, setFilterRatio] = useState("all"); // "all" | "9:16" | "16:9" | "1:1"

  const filteredProjects = projects.filter((p) => {
    const matchesSearch = p.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter =
      filterRatio === "all" ||
      (filterRatio === "9:16" && p.ratioId === "9:16") ||
      (filterRatio === "16:9" && p.ratioId === "16:9") ||
      (filterRatio === "1:1" && p.ratioId === "1:1");
    return matchesSearch && matchesFilter;
  });

  const formatTimeAgo = (timestamp) => {
    if (!timestamp) return "Recently";
    const diff = Date.now() - timestamp;
    const hours = Math.floor(diff / 3600000);
    if (hours < 1) return "Just now";
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  return (
    <div className="splic-dashboard-view">
      {/* Topbar */}
      <header className="splic-dashboard-topbar">
        <div className="splic-dashboard-topbar-left">
          <SplicLogo size={26} showText={true} />
        </div>

        <div className="splic-dashboard-topbar-right">
          <button
            type="button"
            className="splic-btn-primary splic-dash-btn"
            onClick={onNewProject}
          >
            <Plus size={14} strokeWidth={2.5} />
            <span>New Project</span>
          </button>

          <button
            type="button"
            className="splic-btn-secondary splic-dash-btn"
            onClick={onOpenSettings}
            title="Studio Settings"
          >
            <Settings size={15} strokeWidth={1.5} />
            <span>Settings</span>
          </button>

          <button
            type="button"
            className="splic-btn-secondary splic-dash-btn"
            onClick={onOpenSplash}
            title="Splic Home & Walkthroughs"
          >
            <span>Home</span>
          </button>

          {user && (
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginLeft: "4px" }}>
              <div className="splic-user-pill">
                <User size={13} strokeWidth={1.5} style={{ color: "var(--splic-red-primary)" }} />
                <span>{user.name || "Creator"}</span>
              </div>

              {onLogout && (
                <button
                  type="button"
                  className="splic-btn-secondary splic-dash-btn"
                  onClick={onLogout}
                  title="Sign Out"
                >
                  <LogOut size={13} strokeWidth={1.5} />
                  <span>Sign Out</span>
                </button>
              )}
            </div>
          )}
        </div>
      </header>

      {/* Main Content Area */}
      <main className="splic-dashboard-content">
        <div className="splic-dashboard-header-row">
          <div className="splic-dashboard-title-group">
            <h1>Studio Projects</h1>
            <p>Manage, auto-cut, and export your short-form Indic video compositions</p>
            {getStoragePaths()?.db_path ? (
              <p className="splic-projects-storage" title={`Stickers: ${getStoragePaths().stickers_dir}\nRuns: ${getStoragePaths().runs_dir}`}>
                Stored locally in {getStoragePaths().db_path}
              </p>
            ) : null}
          </div>
        </div>

        {/* Filter and Search Bar */}
        <div className="splic-projects-filter-bar">
          <div className="splic-search-input-wrap">
            <Search size={15} strokeWidth={1.5} />
            <input
              type="text"
              className="splic-search-input"
              placeholder="Search projects by name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="splic-filter-pills">
            <button
              type="button"
              className={`splic-filter-pill ${filterRatio === "all" ? "is-active" : ""}`}
              onClick={() => setFilterRatio("all")}
            >
              All Projects
            </button>
            <button
              type="button"
              className={`splic-filter-pill ${filterRatio === "9:16" ? "is-active" : ""}`}
              onClick={() => setFilterRatio("9:16")}
            >
              Reels & Shorts (9:16)
            </button>
            <button
              type="button"
              className={`splic-filter-pill ${filterRatio === "16:9" ? "is-active" : ""}`}
              onClick={() => setFilterRatio("16:9")}
            >
              Landscape (16:9)
            </button>
            <button
              type="button"
              className={`splic-filter-pill ${filterRatio === "1:1" ? "is-active" : ""}`}
              onClick={() => setFilterRatio("1:1")}
            >
              Square (1:1)
            </button>
          </div>
        </div>

        {projectsStatus.state === "loading" && !projects.length ? (
          <div className="splic-projects-status">
            <Loader2 size={15} strokeWidth={1.5} className="splic-projects-spin" />
            <span>Loading your stored projects...</span>
          </div>
        ) : null}
        {projectsStatus.state === "error" ? (
          <div className="splic-projects-status is-error" role="alert">
            <AlertCircle size={15} strokeWidth={1.5} />
            <span>Could not load stored projects. Is the backend running on port 8000? ({projectsStatus.error})</span>
            {onRetryProjects ? (
              <button type="button" className="splic-btn-secondary splic-dash-btn" onClick={onRetryProjects}>
                <RefreshCw size={13} strokeWidth={1.5} />
                <span>Retry</span>
              </button>
            ) : null}
          </div>
        ) : null}
        {projectsStatus.state === "ready" && !projects.length ? (
          <div className="splic-projects-status">
            <Film size={15} strokeWidth={1.5} />
            <span>No stored projects yet. Create one to get started.</span>
          </div>
        ) : null}

        {/* Projects Grid */}
        <div className="splic-projects-grid">
          {/* Card 1: Add New Project Hero Card */}
          <div className="splic-new-project-card" onClick={onNewProject}>
            <div className="splic-new-project-plus">
              <Plus size={26} strokeWidth={2.5} />
            </div>
            <div className="splic-new-project-title">Create New Project</div>
            <div className="splic-new-project-sub">
              Instagram Reel, YouTube Shorts, or 16:9 HD
            </div>
          </div>

          {/* Existing Project Cards */}
          {filteredProjects.map((project) => (
            <div
              key={project.id}
              className={`splic-project-card ${confirmDeleteId === project.id ? "is-confirming-delete" : ""} ${deletingId === project.id ? "is-deleting" : ""}`}
              onClick={() => { if (!deletingId) onOpenProject(project); }}
              onMouseLeave={() => { if (confirmDeleteId === project.id && !deletingId) setConfirmDeleteId(""); }}
            >
              <div className="splic-project-thumb-box">
                {onDeleteProject ? (
                  <div className="splic-project-delete-wrap">
                    {confirmDeleteId === project.id && deletingId !== project.id ? (
                      <button type="button" className="splic-project-delete-cancel" onClick={cancelDelete} title="Keep project" aria-label="Keep project">
                        <X size={13} strokeWidth={1.5} />
                      </button>
                    ) : null}
                    <button
                      type="button"
                      className="splic-project-delete-btn"
                      onClick={(event) => requestDelete(event, project)}
                      disabled={Boolean(deletingId)}
                      title={confirmDeleteId === project.id ? "Click again to delete permanently" : "Delete project"}
                      aria-label={confirmDeleteId === project.id ? `Confirm delete ${project.name}` : `Delete ${project.name}`}
                    >
                      {deletingId === project.id
                        ? <Loader2 size={13} strokeWidth={1.5} className="splic-projects-spin" />
                        : <Trash2 size={13} strokeWidth={1.5} />}
                      {confirmDeleteId === project.id ? <span>{deletingId === project.id ? "Deleting" : "Delete?"}</span> : null}
                    </button>
                  </div>
                ) : null}
                <img
                  src={project.thumbnail || "/assets/sample-portrait.png"}
                  alt={project.name}
                  className="splic-project-thumb-img"
                />
                <span className="splic-project-ratio-badge">
                  {project.platform || project.ratioId}
                </span>
                <span className="splic-project-dur-badge">
                  {project.duration ? `${project.duration.toFixed(1)}s` : "0:00"}
                </span>
              </div>

              <div className="splic-project-card-body">
                <div className="splic-project-name-row">
                  <span className="splic-project-name" title={project.name}>
                    {project.name}
                  </span>
                  <span className={`splic-project-status is-${project.status || "draft"}`}>
                    {STATUS_LABELS[project.status] || project.status || "Draft"}
                  </span>
                </div>

                {project.hasEditPlan ? (
                  <div className="splic-project-info-row" title={project.latestRun?.path || ""}>
                    <span>{projectCountsLine(project) || "Edit plan saved"}</span>
                    {project.runs ? <span>{project.runs} Auto-Cut run{project.runs === 1 ? "" : "s"}</span> : null}
                  </div>
                ) : (
                  <div className="splic-project-info-row"><span>No Auto-Cut yet</span></div>
                )}

                <div className="splic-project-meta-row">
                  <span>{formatTimeAgo(project.updatedAt)}</span>
                  <span style={{ color: "var(--splic-red-primary)", fontWeight: 600 }}>
                    Open Studio →
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}

