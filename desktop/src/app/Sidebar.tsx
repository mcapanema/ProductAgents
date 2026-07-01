import type { ReactNode } from "react";
import { Segmented } from "antd";
import type { Density, Theme } from "../ui/theme";
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
// with `memory` and `reflection` for the two panels missing a nav icon there.
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
  { view: "settings", label: "Settings", icon: "settings" },
  { view: "reflection", label: "Reflection", icon: "reflection" },
];

export function Sidebar({
  view,
  onNavigate,
  theme,
  onThemeChange,
  density,
  onDensityChange,
}: {
  view: View;
  onNavigate: (view: View) => void;
  theme: Theme;
  onThemeChange: (theme: Theme) => void;
  density: Density;
  onDensityChange: (density: Density) => void;
}) {
  return (
    <nav className="sidebar">
      <div className="sidebar-brand">ProductAgents</div>
      <div className="sidebar-controls">
        <Segmented
          aria-label="Theme"
          value={theme}
          onChange={(v) => onThemeChange(v as Theme)}
          options={[
            { label: "Light", value: "light" },
            { label: "Dark", value: "dark" },
          ]}
        />
        <Segmented
          aria-label="Density"
          value={density}
          onChange={(v) => onDensityChange(v as Density)}
          options={[
            { label: "Comfortable", value: "comfortable" },
            { label: "Compact", value: "compact" },
          ]}
        />
      </div>
      <ul className="sidebar-nav">
        {NAV.map((item) => {
          const active = view === item.view;
          return (
            <li key={item.view}>
              <button
                type="button"
                className="sidebar-item"
                aria-current={active ? "page" : undefined}
                onClick={() => onNavigate(item.view)}
              >
                <Icon name={item.icon} />
                <span className="sidebar-label">{item.label}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
