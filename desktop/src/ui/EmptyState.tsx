import type { ReactNode } from "react";
import "./EmptyState.css";

// Inline SVG, 24-grid outline — matches the Sidebar Icon convention. A simple
// "open tray" glyph: the neutral default for "nothing here yet".
const DEFAULT_ICON: ReactNode = (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={1.5}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M4 13.5 6 5.5h12l2 8" />
    <path d="M4 13.5V18a1.5 1.5 0 0 0 1.5 1.5h13A1.5 1.5 0 0 0 20 18v-4.5" />
    <path d="M4 13.5h4l1.2 2h5.6l1.2-2H20" />
  </svg>
);

export function EmptyState({
  title,
  description,
  icon = DEFAULT_ICON,
  action,
}: {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state" role="status">
      <span className="empty-state__icon">{icon}</span>
      <p className="empty-state__title">{title}</p>
      {description && <p className="empty-state__desc">{description}</p>}
      {action && <div className="empty-state__action">{action}</div>}
    </div>
  );
}
