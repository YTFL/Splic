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
} from "lucide-react";
import { SplicLogo } from "./SplicLogo.jsx";

export function ProjectsDashboard({
  projects = [],
  onOpenProject,
  onNewProject,
  onOpenSettings,
  onOpenSplash,
  onDeleteProject,
  user,
  onLogout,
}) {
  const [searchQuery, setSearchQuery] = useState("");
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
              className="splic-project-card"
              onClick={() => onOpenProject(project)}
            >
              <div className="splic-project-thumb-box">
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
                </div>

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

