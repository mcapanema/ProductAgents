import type { ReactNode } from "react";

// Inline SVG, 24-grid outline — matches the Sidebar Icon convention. One
// glyph per screen (mirroring that screen's own nav icon) so empty states
// no longer all show the same default tray.
const PATHS: Record<string, ReactNode> = {
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
  reflection: (
    <>
      <path d="M3.5 12a8.5 8.5 0 1 0 2.9-6.4" />
      <path d="M3.5 4.5v4.6h4.6" />
      <path d="M12 7.5V12l3 2" />
    </>
  ),
};

export function EmptyStateIcon({ name }: { name: keyof typeof PATHS }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {PATHS[name]}
    </svg>
  );
}
