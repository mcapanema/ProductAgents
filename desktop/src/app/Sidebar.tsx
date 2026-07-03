import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import "./Sidebar.css";

export type View =
  | "run"
  | "workflows"
  | "sessions"
  | "decisions"
  | "connectors"
  | "prompts"
  | "settings"
  | "reflection"
  | "memory";

// Inline SVG, 24-grid, outline style — ported from
// design/styleguide/src/phase3/Phase3Navigation.tsx (Icon/ICONS), extended
// with `memory` and `reflection` (missing there) plus the two rail-toggle
// arrows.
const ICONS: Record<string, ReactNode> = {
  run: <path d="M3 12h3.5l2.5 7 4-15 2.5 8H21" />,
  workflows: (
    <>
      <circle cx="6" cy="6" r="2.2" />
      <circle cx="18" cy="6" r="2.2" />
      <circle cx="12" cy="18" r="2.2" />
      <path d="M6 8.2v1.3a3 3 0 0 0 3 3h6a3 3 0 0 0 3-3V8.2" />
      <path d="M12 12.8v3" />
    </>
  ),
  sessions: (
    <>
      <circle cx="12" cy="12" r="8.2" />
      <path d="M12 7.5V12l3 1.8" />
    </>
  ),
  decisions: (
    <>
      <circle cx="12" cy="12" r="8.2" />
      <path d="M8.5 12l2.4 2.4 4.6-5" />
    </>
  ),
  memory: (
    <>
      <ellipse cx="12" cy="6" rx="7" ry="3" />
      <path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6" />
      <path d="M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6" />
    </>
  ),
  connectors: (
    <>
      <path d="M9 3v5" />
      <path d="M15 3v5" />
      <path d="M7 8h10v3a5 5 0 0 1-10 0z" />
      <path d="M12 16v5" />
    </>
  ),
  prompts: (
    <>
      <rect x="3" y="4.5" width="18" height="15" rx="2" />
      <path d="M7.5 9.5l3 2.5-3 2.5" />
      <path d="M13 14.5h4" />
    </>
  ),
  settings: (
    <>
      <path d="M4 6.5h16" />
      <path d="M4 12h16" />
      <path d="M4 17.5h16" />
      <circle cx="9" cy="6.5" r="2.1" />
      <circle cx="15" cy="12" r="2.1" />
      <circle cx="8" cy="17.5" r="2.1" />
    </>
  ),
  reflection: (
    <>
      <path d="M3.5 12a8.5 8.5 0 1 0 2.9-6.4" />
      <path d="M3.5 4.5v4.6h4.6" />
      <path d="M12 7.5V12l3 2" />
    </>
  ),
  "arrow-left": (
    <>
      <path d="M19 12H5" />
      <path d="M12 19l-7-7 7-7" />
    </>
  ),
  "arrow-right": (
    <>
      <path d="M5 12h14" />
      <path d="M12 5l7 7-7 7" />
    </>
  ),
};

function Icon({ name }: { name: string }) {
  return (
    <svg
      className="sidebar-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {ICONS[name]}
    </svg>
  );
}

const NAV: { view: View; label: string; icon: string }[] = [
  { view: "run", label: "Run", icon: "run" },
  { view: "workflows", label: "Workflows", icon: "workflows" },
  { view: "sessions", label: "Sessions", icon: "sessions" },
  { view: "decisions", label: "Decisions", icon: "decisions" },
  { view: "memory", label: "Memory", icon: "memory" },
  { view: "connectors", label: "Connectors", icon: "connectors" },
  { view: "prompts", label: "Prompts", icon: "prompts" },
  { view: "reflection", label: "Reflection", icon: "reflection" },
  { view: "settings", label: "Settings", icon: "settings" },
];

const COLLAPSE_STORAGE_KEY = "pa-sidebar-collapsed";

function readStoredCollapsed(): boolean {
  return localStorage.getItem(COLLAPSE_STORAGE_KEY) === "1";
}

export function Sidebar({
  view,
  onNavigate,
  running,
}: {
  view: View;
  onNavigate: (view: View) => void;
  running: boolean;
}) {
  const [collapsed, setCollapsed] = useState(readStoredCollapsed);

  useEffect(() => {
    localStorage.setItem(COLLAPSE_STORAGE_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  return (
    <nav aria-label="Sidebar" className={`sidebar${collapsed ? " is-collapsed" : ""}`}>
      {!collapsed && <div className="sidebar-brand">ProductAgents</div>}
      <ul className="sidebar-nav">
        {NAV.map((item) => {
          const active = view === item.view;
          return (
            <li key={item.view}>
              <button
                type="button"
                className="sidebar-item"
                aria-current={active ? "page" : undefined}
                aria-label={collapsed || (item.view === "run" && running) ? item.label : undefined}
                title={collapsed ? item.label : undefined}
                onClick={() => onNavigate(item.view)}
              >
                <Icon name={item.icon} />
                {!collapsed && <span className="sidebar-label">{item.label}</span>}
                {item.view === "run" && running && (
                  <span className="status-dot status-dot--live" role="img" aria-label="run in progress" />
                )}
              </button>
            </li>
          );
        })}
      </ul>
      <button
        type="button"
        className="sidebar-toggle"
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        onClick={() => setCollapsed((c) => !c)}
      >
        <Icon name={collapsed ? "arrow-right" : "arrow-left"} />
      </button>
    </nav>
  );
}
