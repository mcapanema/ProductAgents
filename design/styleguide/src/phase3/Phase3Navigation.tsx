// Phase 3B — Navigation. Wayfinding & command surfaces for the resource-explorer
// IA: sidebar / rail, tree, breadcrumbs, tabs, the ⌘K command palette, quick
// switcher, search, pagination, stepper, context menu. CSS lives in
// ./phase3b-navigation.css (imported once in main.tsx). Tokens only.
import { useEffect, useRef, useState } from "react";
import type React from "react";
import { Section, Specimen } from "../sg";

/* ─────────────────────────────────────────────────────────── icons ───
 * Phosphor-style inline SVG, 24-grid, outline. `fill` stays "none" — the
 * selected/active item is signalled by accent color + marker + bg, never by a
 * filled glyph alone (keeps color off the single-channel hook). */
const ICONS: Record<string, React.ReactNode> = {
  "chevron-right": <path d="M9 6l6 6-6 6" />,
  "chevron-down": <path d="M6 9l6 6 6-6" />,
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
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.3-4.3" />
    </>
  ),
  x: <path d="M6 6l12 12M18 6L6 18" />,
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
  folder: <path d="M3 6.5a2 2 0 0 1 2-2h3.6l2 2H19a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />,
  file: (
    <>
      <path d="M14 3.5H7a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8.5z" />
      <path d="M14 3.5v5h5" />
    </>
  ),
  check: <path d="M5 12l4.5 4.5L19 7" />,
  copy: (
    <>
      <rect x="9" y="9" width="11" height="11" rx="2" />
      <path d="M5 15V5a2 2 0 0 1 2-2h8" />
    </>
  ),
  pencil: (
    <>
      <path d="M4 20h4L19 9l-4-4L4 16z" />
      <path d="M13.5 6.5l4 4" />
    </>
  ),
  trash: (
    <>
      <path d="M4 7h16" />
      <path d="M9.5 7V4.5h5V7" />
      <path d="M6.5 7l1 13h9l1-13" />
    </>
  ),
  external: (
    <>
      <path d="M14 4h6v6" />
      <path d="M20 4l-9 9" />
      <path d="M18 13.5V18a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4.5" />
    </>
  ),
  warning: (
    <>
      <path d="M12 4l9 16H3z" />
      <path d="M12 10v4" />
      <path d="M12 17h.01" />
    </>
  ),
  diamond: <path d="M12 3l9 9-9 9-9-9z" />,
};

function Icon({ name, size = "var(--size-icon-inline)" }: { name: string; size?: string }) {
  return (
    <svg
      className="nv-icon"
      viewBox="0 0 24 24"
      style={{ width: size, height: size }}
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

/* Keyboard hint chips — a row of mono key caps. */
function Keys({ keys }: { keys: string[] }) {
  return (
    <span className="nv-keys">
      {keys.map((k, i) => (
        <kbd key={i} className="nv-kbd">
          {k}
        </kbd>
      ))}
    </span>
  );
}

/* The seven resources of the explorer IA (CLAUDE.md / context §4). */
const RESOURCES = [
  { id: "run", label: "Run", icon: "run" },
  { id: "workflows", label: "Workflows", icon: "workflows" },
  { id: "sessions", label: "Sessions", icon: "sessions" },
  { id: "decisions", label: "Decisions", icon: "decisions" },
  { id: "connectors", label: "Connectors", icon: "connectors" },
  { id: "prompts", label: "Prompts", icon: "prompts" },
  { id: "settings", label: "Settings", icon: "settings" },
] as const;

/* ──────────────────────────────────────────────────────── sidebar ─── */
function SidebarNav() {
  const [sel, setSel] = useState("decisions");
  return (
    <nav className="nv-sidebar" aria-label="Resources">
      <ul className="nv-sidebar-list">
        {RESOURCES.map((r) => {
          const active = sel === r.id;
          return (
            <li key={r.id}>
              <button
                type="button"
                className="nv-sidebar-item"
                aria-current={active ? "page" : undefined}
                onClick={() => setSel(r.id)}
              >
                <Icon name={r.icon} size="var(--size-icon)" />
                <span className="nv-sidebar-label">{r.label}</span>
                {r.id === "run" && (
                  <span className="nv-dot nv-dot--live" role="img" aria-label="run in progress" />
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

/* ──────────────────────────────────────────── navigation rail ─── */
function NavRail() {
  const [sel, setSel] = useState("decisions");
  return (
    <nav className="nv-rail" aria-label="Resources (collapsed)">
      {RESOURCES.map((r) => {
        const active = sel === r.id;
        return (
          <button
            key={r.id}
            type="button"
            className="nv-rail-item"
            aria-label={r.label}
            aria-current={active ? "page" : undefined}
            title={r.label}
            onClick={() => setSel(r.id)}
          >
            <Icon name={r.icon} size="var(--size-icon)" />
            {r.id === "run" && (
              <span className="nv-dot nv-dot--live nv-rail-dot" role="img" aria-label="run in progress" />
            )}
          </button>
        );
      })}
    </nav>
  );
}

/* ─────────────────────────────────────────────────────── tree ─── */
type TreeNode = { id: string; label: string; icon: string; children?: TreeNode[] };
const TREE: TreeNode[] = [
  {
    id: "decisions",
    label: "Decisions",
    icon: "folder",
    children: [
      {
        id: "q3",
        label: "2026-Q3",
        icon: "folder",
        children: [
          { id: "checkout", label: "Expand Checkout to EU", icon: "decisions" },
          { id: "pricing", label: "Usage-based pricing v2", icon: "decisions" },
        ],
      },
      {
        id: "q2",
        label: "2026-Q2",
        icon: "folder",
        children: [{ id: "sso", label: "Enterprise SSO", icon: "decisions" }],
      },
    ],
  },
  {
    id: "connectors",
    label: "Connectors",
    icon: "folder",
    children: [
      { id: "github", label: "github.com/acme", icon: "file" },
      { id: "jira", label: "acme.atlassian.net", icon: "file" },
    ],
  },
];

type Flat = { node: TreeNode; depth: number; parentId: string | null; hasChildren: boolean };
function flatten(nodes: TreeNode[], expanded: Set<string>, depth = 0, parentId: string | null = null): Flat[] {
  const out: Flat[] = [];
  for (const node of nodes) {
    const hasChildren = !!(node.children && node.children.length);
    out.push({ node, depth, parentId, hasChildren });
    if (hasChildren && expanded.has(node.id)) {
      out.push(...flatten(node.children as TreeNode[], expanded, depth + 1, node.id));
    }
  }
  return out;
}

// ponytail: flat treeitem list with aria-level instead of nested role=group —
// AT reads level/expanded fine; nest into groups if a real tree ships.
function TreeView() {
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set(["decisions", "q3"]));
  const [sel, setSel] = useState("checkout");
  const [focusId, setFocusId] = useState("decisions");

  const flat = flatten(TREE, expanded);
  const visible = flat.map((f) => f.node.id);
  const effFocus = visible.includes(focusId) ? focusId : flat[0].node.id;

  function toggle(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function onKey(e: React.KeyboardEvent<HTMLUListElement>) {
    const idx = flat.findIndex((f) => f.node.id === effFocus);
    if (idx < 0) return;
    const cur = flat[idx];
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setFocusId(flat[Math.min(idx + 1, flat.length - 1)].node.id);
        break;
      case "ArrowUp":
        e.preventDefault();
        setFocusId(flat[Math.max(idx - 1, 0)].node.id);
        break;
      case "ArrowRight":
        e.preventDefault();
        if (cur.hasChildren && !expanded.has(cur.node.id)) toggle(cur.node.id);
        else if (cur.hasChildren) setFocusId(flat[idx + 1].node.id);
        break;
      case "ArrowLeft":
        e.preventDefault();
        if (cur.hasChildren && expanded.has(cur.node.id)) toggle(cur.node.id);
        else if (cur.parentId) setFocusId(cur.parentId);
        break;
      case "Enter":
      case " ":
        e.preventDefault();
        if (cur.hasChildren) toggle(cur.node.id);
        else setSel(cur.node.id);
        break;
    }
  }

  return (
    <ul className="nv-tree" role="tree" aria-label="Resource tree" onKeyDown={onKey}>
      {flat.map((f) => {
        const isOpen = expanded.has(f.node.id);
        const selected = sel === f.node.id;
        return (
          <li
            key={f.node.id}
            role="treeitem"
            aria-level={f.depth + 1}
            aria-expanded={f.hasChildren ? isOpen : undefined}
            aria-selected={selected}
            tabIndex={effFocus === f.node.id ? 0 : -1}
            className={"nv-tree-item" + (selected ? " is-selected" : "")}
            style={{ "--nv-depth": f.depth } as React.CSSProperties}
            onFocus={() => setFocusId(f.node.id)}
            onClick={() => {
              setFocusId(f.node.id);
              if (f.hasChildren) toggle(f.node.id);
              else setSel(f.node.id);
            }}
          >
            <span className="nv-tree-row">
              {f.hasChildren ? (
                <Icon name={isOpen ? "chevron-down" : "chevron-right"} size="var(--icon-sm)" />
              ) : (
                <span className="nv-tree-spacer" />
              )}
              <Icon name={f.node.icon} size="var(--icon-sm)" />
              <span className="nv-tree-label">{f.node.label}</span>
            </span>
          </li>
        );
      })}
    </ul>
  );
}

/* ────────────────────────────────────────────────── breadcrumbs ─── */
function Breadcrumbs() {
  const trail = [
    { label: "Decisions" },
    { label: "2026-Q3" },
    { label: "Expand Checkout to EU" },
  ];
  return (
    <nav className="nv-crumbs" aria-label="Breadcrumb">
      <ol>
        {trail.map((c, i) => {
          const last = i === trail.length - 1;
          return (
            <li key={c.label}>
              {last ? (
                <span className="nv-crumb is-current" aria-current="page">
                  {c.label}
                </span>
              ) : (
                <a className="nv-crumb" href="#" onClick={(e) => e.preventDefault()}>
                  {c.label}
                </a>
              )}
              {!last && <Icon name="chevron-right" size="var(--icon-xs)" />}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

/* ─────────────────────────────────────────────────────── tabs ─── */
const TAB_LABELS = ["Evidence", "Debate", "Risk", "Recommendation"];
function Tabs({ variant }: { variant: "underline" | "segmented" }) {
  const [active, setActive] = useState(0);
  const ref = useRef<HTMLDivElement>(null);

  function focusTab(i: number) {
    setActive(i);
    ref.current?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[i]?.focus();
  }
  function onKey(e: React.KeyboardEvent<HTMLDivElement>) {
    if (e.key === "ArrowRight") {
      e.preventDefault();
      focusTab((active + 1) % TAB_LABELS.length);
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      focusTab((active - 1 + TAB_LABELS.length) % TAB_LABELS.length);
    } else if (e.key === "Home") {
      e.preventDefault();
      focusTab(0);
    } else if (e.key === "End") {
      e.preventDefault();
      focusTab(TAB_LABELS.length - 1);
    }
  }
  return (
    <div
      ref={ref}
      role="tablist"
      aria-label="Decision facets"
      className={`nv-tablist nv-tablist--${variant}`}
      onKeyDown={onKey}
    >
      {TAB_LABELS.map((t, i) => (
        <button
          key={t}
          type="button"
          role="tab"
          aria-selected={active === i}
          tabIndex={active === i ? 0 : -1}
          className="nv-tab"
          onClick={() => setActive(i)}
        >
          {t}
        </button>
      ))}
    </div>
  );
}

/* ──────────────────────────────────────────── command palette ⭐ ─── */
type Cmd = { group: string; icon: string; label: string; hint?: string[] };
const COMMANDS: Cmd[] = [
  { group: "Jump to", icon: "run", label: "Run", hint: ["G", "R"] },
  { group: "Jump to", icon: "workflows", label: "Workflows", hint: ["G", "W"] },
  { group: "Jump to", icon: "sessions", label: "Sessions", hint: ["G", "S"] },
  { group: "Jump to", icon: "decisions", label: "Decisions", hint: ["G", "D"] },
  { group: "Jump to", icon: "connectors", label: "Connectors", hint: ["G", "C"] },
  { group: "Actions", icon: "run", label: "Start new decision run…", hint: ["⌘", "N"] },
  { group: "Actions", icon: "connectors", label: "Sync all connectors", hint: ["⌘", "Y"] },
  { group: "Actions", icon: "prompts", label: "Edit active prompt", hint: ["⌘", "E"] },
  { group: "Actions", icon: "settings", label: "Switch model provider…" },
  { group: "Recent", icon: "decisions", label: "Expand Checkout to EU" },
  { group: "Recent", icon: "decisions", label: "Usage-based pricing v2" },
];

function highlight(text: string, q: string): React.ReactNode {
  const query = q.trim();
  if (!query) return text;
  const at = text.toLowerCase().indexOf(query.toLowerCase());
  if (at < 0) return text;
  return (
    <>
      {text.slice(0, at)}
      <mark className="nv-mark">{text.slice(at, at + query.length)}</mark>
      {text.slice(at + query.length)}
    </>
  );
}

function CommandPalette() {
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const [ran, setRan] = useState<string | null>(null);

  const filtered = COMMANDS.filter((c) => c.label.toLowerCase().includes(q.toLowerCase().trim()));
  const groups: { name: string; items: { cmd: Cmd; flatIndex: number }[] }[] = [];
  filtered.forEach((cmd, i) => {
    let g = groups.find((x) => x.name === cmd.group);
    if (!g) {
      g = { name: cmd.group, items: [] };
      groups.push(g);
    }
    g.items.push({ cmd, flatIndex: i });
  });

  function move(d: number) {
    if (filtered.length === 0) return;
    setSel((s) => (s + d + filtered.length) % filtered.length);
  }
  function run(i: number) {
    const c = filtered[i];
    if (c) setRan(c.label);
  }
  function onChange(v: string) {
    setQ(v);
    setSel(0);
    setRan(null);
  }
  function onKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      move(1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      move(-1);
    } else if (e.key === "Enter") {
      e.preventDefault();
      run(sel);
    } else if (e.key === "Escape") {
      e.preventDefault();
      onChange("");
    }
  }

  return (
    <div className="nv-palette" role="dialog" aria-label="Command palette">
      <div className="nv-palette-head">
        <Icon name="search" size="var(--size-icon)" />
        <input
          className="nv-palette-input"
          type="text"
          role="combobox"
          aria-expanded="true"
          aria-controls="nv-palette-list"
          aria-autocomplete="list"
          aria-activedescendant={filtered[sel] ? `nv-cmd-${sel}` : undefined}
          placeholder="Search actions, decisions, connectors…"
          value={q}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKey}
        />
        <Keys keys={["⌘", "K"]} />
      </div>

      <ul className="nv-palette-list" id="nv-palette-list" role="listbox" aria-label="Results">
        {groups.length === 0 && (
          <li className="nv-palette-empty">No commands match “{q.trim()}”.</li>
        )}
        {groups.map((g) => (
          <li key={g.name} className="nv-palette-group">
            <div className="nv-palette-group-head">{g.name}</div>
            <ul>
              {g.items.map(({ cmd, flatIndex }) => {
                const isActive = flatIndex === sel;
                return (
                  <li
                    key={cmd.label}
                    id={`nv-cmd-${flatIndex}`}
                    role="option"
                    aria-selected={isActive}
                    className={"nv-palette-item" + (isActive ? " is-active" : "")}
                    onMouseMove={() => setSel(flatIndex)}
                    onClick={() => run(flatIndex)}
                  >
                    <Icon name={cmd.icon} />
                    <span className="nv-palette-label">{highlight(cmd.label, q)}</span>
                    {cmd.hint && <Keys keys={cmd.hint} />}
                  </li>
                );
              })}
            </ul>
          </li>
        ))}
      </ul>

      <div className="nv-palette-foot">
        <span className="nv-hintset">
          <Keys keys={["↑", "↓"]} /> navigate
        </span>
        <span className="nv-hintset">
          <Keys keys={["↵"]} /> {ran ? `ran: ${ran}` : "select"}
        </span>
        <span className="nv-hintset nv-hintset--end">
          <Keys keys={["esc"]} /> dismiss
        </span>
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────── quick switcher ─── */
type Switchable = { label: string; meta: string; state: "running" | "done" };
const SWITCH: Switchable[] = [
  { label: "Usage-based pricing v2", meta: "run · live", state: "running" },
  { label: "Expand Checkout to EU", meta: "decision · 2h ago", state: "done" },
  { label: "Enterprise SSO", meta: "decision · 1d ago", state: "done" },
  { label: "Churn root-cause analysis", meta: "session · 3d ago", state: "done" },
];
function QuickSwitcher() {
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const list = SWITCH.filter((s) => s.label.toLowerCase().includes(q.toLowerCase().trim()));
  function onKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (list.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSel((s) => (s + 1) % list.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSel((s) => (s - 1 + list.length) % list.length);
    }
  }
  return (
    <div className="nv-switcher" role="dialog" aria-label="Quick switcher">
      <div className="nv-switcher-head">
        <span className="nv-switcher-prefix">Switch to</span>
        <input
          className="nv-switcher-input"
          type="text"
          role="combobox"
          aria-expanded="true"
          aria-controls="nv-switcher-list"
          aria-activedescendant={list[sel] ? `nv-sw-${sel}` : undefined}
          placeholder="Type a session or decision…"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setSel(0);
          }}
          onKeyDown={onKey}
        />
      </div>
      <ul className="nv-switcher-list" id="nv-switcher-list" role="listbox">
        {list.map((s, i) => (
          <li
            key={s.label}
            id={`nv-sw-${i}`}
            role="option"
            aria-selected={i === sel}
            className={"nv-switcher-item" + (i === sel ? " is-active" : "")}
            onMouseMove={() => setSel(i)}
          >
            <span className="nv-switcher-main">
              <span className="nv-switcher-label">{s.label}</span>
              <span className="nv-switcher-meta">{s.meta}</span>
            </span>
            {s.state === "running" ? (
              <span className="nv-state nv-state--running">
                <span className="nv-dot nv-dot--live" /> live
              </span>
            ) : (
              <span className="nv-state nv-state--done">
                <Icon name="check" size="var(--icon-xs)" /> done
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ────────────────────────────────────────────────── search bar ─── */
function SearchBar() {
  const [v, setV] = useState("checkout");
  return (
    <div className="nv-search">
      <Icon name="search" size="var(--size-icon-inline)" />
      <input
        className="nv-search-input"
        type="text"
        aria-label="Search decisions"
        placeholder="Search decisions…"
        value={v}
        onChange={(e) => setV(e.target.value)}
      />
      {v && (
        <button type="button" className="nv-search-clear" aria-label="Clear search" onClick={() => setV("")}>
          <Icon name="x" size="var(--icon-sm)" />
        </button>
      )}
    </div>
  );
}

/* ──────────────────────────────── search + filters + order ─── */
/* Status meta — color + glyph + label (color is never the only channel). */
type StatusId = "approved" | "degraded" | "failed" | "awaiting";
const STATUS: Record<StatusId, { label: string; icon: string; tone: string }> = {
  // `tone` is the contrast-safe TEXT step (not the 500 fill) so the small status
  // labels clear 4.5:1 on the light theme; --ai-awaiting-human is already at the
  // link level (indigo-600 light / 400 dark). Each status also carries a glyph.
  approved: { label: "Approved", icon: "check", tone: "--ai-done-text" },
  degraded: { label: "Degraded", icon: "warning", tone: "--ai-degraded-text" },
  failed: { label: "Failed", icon: "x", tone: "--ai-failed-text" },
  awaiting: { label: "Awaiting you", icon: "diamond", tone: "--ai-awaiting-human" },
};
type Decision = { id: string; title: string; status: StatusId; date: string; ts: number; confidence: number };
const DECISIONS: Decision[] = [
  { id: "dec-1042", title: "Adopt usage-based pricing tier", status: "approved", date: "Jun 28", ts: 8, confidence: 0.82 },
  { id: "dec-1041", title: "Sunset legacy mobile SDK v2", status: "degraded", date: "Jun 27", ts: 7, confidence: 0.64 },
  { id: "dec-1040", title: "Prioritize SSO for enterprise", status: "approved", date: "Jun 26", ts: 6, confidence: 0.91 },
  { id: "dec-1039", title: "Launch AI changelog digest", status: "failed", date: "Jun 25", ts: 5, confidence: 0.48 },
  { id: "dec-1038", title: "Expand to EU data residency", status: "awaiting", date: "Jun 24", ts: 4, confidence: 0.73 },
  { id: "dec-1037", title: "Bundle analytics into the Pro plan", status: "approved", date: "Jun 22", ts: 3, confidence: 0.79 },
  { id: "dec-1036", title: "Deprecate REST v1 endpoints", status: "degraded", date: "Jun 20", ts: 2, confidence: 0.61 },
  { id: "dec-1035", title: "Self-serve onboarding checklist", status: "approved", date: "Jun 18", ts: 1, confidence: 0.86 },
];
const SORTS: { id: string; label: string }[] = [
  { id: "relevance", label: "Relevance" },
  { id: "newest", label: "Newest" },
  { id: "confidence", label: "Confidence" },
  { id: "az", label: "A–Z" },
];

function SearchExplorer() {
  const [q, setQ] = useState("");
  const [active, setActive] = useState<Set<StatusId>>(new Set());
  const [sort, setSort] = useState("relevance");

  function toggleStatus(s: StatusId) {
    setActive((prev) => {
      const next = new Set(prev);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      return next;
    });
  }

  const query = q.trim().toLowerCase();
  const filtered = DECISIONS.filter(
    (d) => d.title.toLowerCase().includes(query) && (active.size === 0 || active.has(d.status)),
  );
  const sorted = [...filtered].sort((a, b) => {
    switch (sort) {
      case "newest": return b.ts - a.ts;
      case "confidence": return b.confidence - a.confidence;
      case "az": return a.title.localeCompare(b.title);
      default: // relevance — earliest match position first; fall back to newest
        if (!query) return b.ts - a.ts;
        return a.title.toLowerCase().indexOf(query) - b.title.toLowerCase().indexOf(query) || b.ts - a.ts;
    }
  });

  return (
    <div className="nv-explorer">
      <div className="nv-search">
        <Icon name="search" size="var(--size-icon-inline)" />
        <input
          className="nv-search-input"
          type="text"
          aria-label="Search decisions"
          placeholder="Search decisions…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        {q && (
          <button type="button" className="nv-search-clear" aria-label="Clear search" onClick={() => setQ("")}>
            <Icon name="x" size="var(--icon-sm)" />
          </button>
        )}
      </div>

      <div className="nv-controls">
        <div className="nv-filter-chips" role="group" aria-label="Filter by status">
          {(Object.keys(STATUS) as StatusId[]).map((id) => {
            const s = STATUS[id];
            const on = active.has(id);
            return (
              <button
                key={id}
                type="button"
                className={`nv-filter-chip${on ? " is-active" : ""}`}
                aria-pressed={on}
                onClick={() => toggleStatus(id)}
              >
                <span className="nv-chip-ico" style={{ color: `var(${s.tone})` }}>
                  <Icon name={s.icon} size="var(--icon-xs)" />
                </span>
                {s.label}
              </button>
            );
          })}
          {active.size > 0 && (
            <button type="button" className="nv-filter-clear" onClick={() => setActive(new Set())}>
              Clear filters
            </button>
          )}
        </div>
        <label className="nv-sort">
          <span className="nv-sort-label">Sort</span>
          <select aria-label="Sort results" value={sort} onChange={(e) => setSort(e.target.value)}>
            {SORTS.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="nv-count" aria-live="polite">
        {sorted.length} of {DECISIONS.length} decisions
      </div>

      <ul className="nv-results">
        {sorted.length === 0 ? (
          <li className="nv-empty">No decisions match “{q.trim()}”{active.size > 0 ? " with these filters" : ""}.</li>
        ) : (
          sorted.map((d) => {
            const s = STATUS[d.status];
            return (
              <li className="nv-result" key={d.id}>
                <span className="nv-result-main">
                  <span className="nv-result-title">{highlight(d.title, q)}</span>
                  <span className="nv-result-id">{d.id}</span>
                </span>
                <span className="nv-result-meta">
                  <span className="nv-result-status" style={{ color: `var(${s.tone})` }}>
                    <Icon name={s.icon} size="var(--icon-xs)" />
                    {s.label}
                  </span>
                  <span className="nv-result-conf">{Math.round(d.confidence * 100)}%</span>
                  <span className="nv-result-date">{d.date}</span>
                </span>
              </li>
            );
          })
        )}
      </ul>
    </div>
  );
}

/* ────────────────────────────────────────────────── pagination ─── */
function pageList(cur: number, total: number): (number | "…")[] {
  const out: (number | "…")[] = [];
  for (let p = 1; p <= total; p++) {
    if (p === 1 || p === total || Math.abs(p - cur) <= 1) out.push(p);
    else if (out[out.length - 1] !== "…") out.push("…");
  }
  return out;
}
function Pagination() {
  const total = 9;
  const [page, setPage] = useState(4);
  return (
    <nav className="nv-pagination" aria-label="Pagination">
      <ul className="nv-pager">
        <li>
          <button
            type="button"
            className="nv-page-arrow"
            aria-label="Previous page"
            disabled={page === 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            <Icon name="arrow-left" size="var(--icon-sm)" />
          </button>
        </li>
        {pageList(page, total).map((p, i) =>
          p === "…" ? (
            <li key={`gap-${i}`} aria-hidden="true" className="nv-ellipsis">
              …
            </li>
          ) : (
            <li key={p}>
              <button
                type="button"
                className="nv-page"
                aria-label={`Page ${p}`}
                aria-current={p === page ? "page" : undefined}
                onClick={() => setPage(p)}
              >
                {p}
              </button>
            </li>
          ),
        )}
        <li>
          <button
            type="button"
            className="nv-page-arrow"
            aria-label="Next page"
            disabled={page === total}
            onClick={() => setPage((p) => Math.min(total, p + 1))}
          >
            <Icon name="arrow-right" size="var(--icon-sm)" />
          </button>
        </li>
      </ul>
    </nav>
  );
}

/* ───────────────────────────────────────────────────── stepper ─── */
const STEPS = ["Evidence", "Analysis", "Debate", "Decision", "Approval"];
function Stepper() {
  const [cur, setCur] = useState(2);
  return (
    <div className="nv-stepper-wrap">
      <ol className="nv-stepper">
        {STEPS.map((s, i) => {
          const state = i < cur ? "done" : i === cur ? "current" : "upcoming";
          return (
            <li key={s} className={`nv-step is-${state}`} aria-current={i === cur ? "step" : undefined}>
              <span className="nv-step-marker">
                {state === "done" ? (
                  <Icon name="check" size="var(--icon-sm)" />
                ) : (
                  <span className="nv-step-num">{i + 1}</span>
                )}
              </span>
              <span className="nv-step-label">{s}</span>
            </li>
          );
        })}
      </ol>
      <div className="nv-stepper-ctl">
        <button className="nv-btn" type="button" disabled={cur === 0} onClick={() => setCur((c) => Math.max(0, c - 1))}>
          Back
        </button>
        <button
          className="nv-btn nv-btn--accent"
          type="button"
          disabled={cur === STEPS.length - 1}
          onClick={() => setCur((c) => Math.min(STEPS.length - 1, c + 1))}
        >
          Next
        </button>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────── context menu ─── */
type MenuItem =
  | { kind: "sep" }
  | { kind: "item"; icon: string; label: string; keys?: string[]; danger?: boolean };
const MENU: MenuItem[] = [
  { kind: "item", icon: "copy", label: "Copy decision ID", keys: ["⌘", "C"] },
  { kind: "item", icon: "external", label: "Open in new view", keys: ["⌘", "↵"] },
  { kind: "sep" },
  { kind: "item", icon: "pencil", label: "Rename…", keys: ["F2"] },
  { kind: "item", icon: "prompts", label: "Re-run with edits", keys: ["⌘", "R"] },
  { kind: "sep" },
  { kind: "item", icon: "trash", label: "Delete decision", keys: ["⌫"], danger: true },
];
type MenuItemRow = Extract<MenuItem, { kind: "item" }>;

function ContextMenu() {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const [active, setActive] = useState(0);
  const menuRef = useRef<HTMLDivElement>(null);
  const areaRef = useRef<HTMLDivElement>(null);

  const focusable = MENU.map((it, i) => ({ it, i })).filter(
    (x): x is { it: MenuItemRow; i: number } => x.it.kind === "item",
  );

  useEffect(() => {
    if (open) menuRef.current?.focus();
  }, [open]);

  function openAt(e: React.MouseEvent) {
    e.preventDefault();
    const rect = areaRef.current?.getBoundingClientRect();
    if (!rect) return;
    setPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    setActive(0);
    setOpen(true);
  }
  function onKey(e: React.KeyboardEvent) {
    if (e.key === "Escape") setOpen(false);
    else if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => (a + 1) % focusable.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => (a - 1 + focusable.length) % focusable.length);
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      setOpen(false);
    }
  }

  return (
    <div
      className="nv-ctx-area"
      ref={areaRef}
      onContextMenu={openAt}
      onClick={() => setOpen(false)}
    >
      <span className="nv-ctx-hint">Right-click anywhere in this panel</span>
      {open && (
        <div
          className="nv-ctx-menu"
          role="menu"
          aria-label="Decision actions"
          tabIndex={-1}
          ref={menuRef}
          onKeyDown={onKey}
          aria-activedescendant={focusable[active] ? `nv-ctx-${focusable[active].i}` : undefined}
          style={{ left: pos.x, top: pos.y }}
        >
          {MENU.map((it, i) => {
            if (it.kind === "sep") return <div key={i} className="nv-ctx-sep" role="separator" />;
            const fIdx = focusable.findIndex((x) => x.i === i);
            return (
              <button
                key={i}
                id={`nv-ctx-${i}`}
                role="menuitem"
                type="button"
                className={
                  "nv-ctx-item" +
                  (it.danger ? " is-danger" : "") +
                  (fIdx === active ? " is-active" : "")
                }
                onMouseMove={() => setActive(fIdx)}
                onClick={(e) => {
                  e.stopPropagation();
                  setOpen(false);
                }}
              >
                <Icon name={it.icon} />
                <span className="nv-ctx-label">{it.label}</span>
                {it.keys && <Keys keys={it.keys} />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ───────────────────────────────────────────────── the gallery ─── */
export function Phase3Navigation() {
  return (
    <>
      <div className="sg-subband">
        <h3>3B · Navigation</h3>
        <span>Wayfinding &amp; command surfaces — sidebar, tree, tabs, the ⌘K palette, menus.</span>
      </div>

      <Section
        id="nav-sidebar"
        title="Sidebar & Navigation Rail"
        desc="The resource spine of the explorer IA. Selected = tinted ground + accent marker + accent icon + bold (color is never alone). Run carries an amber live dot — amber means running, never interaction."
      >
        <div className="sg-card">
          <Specimen label="Sidebar">
            <SidebarNav />
          </Specimen>
          <Specimen label="Rail (collapsed)">
            <NavRail />
          </Specimen>
        </div>
      </Section>

      <Section
        id="nav-tree"
        title="Tree View"
        desc="Hierarchical browse (decisions by quarter, connectors). Full keyboard tree: ↑↓ move, → expand / dive, ← collapse / out, Enter toggles or selects."
      >
        <div className="sg-card">
          <Specimen label="Resource tree">
            <TreeView />
          </Specimen>
        </div>
      </Section>

      <Section
        id="nav-breadcrumbs"
        title="Breadcrumbs"
        desc="Where am I in the hierarchy. Trailing crumb is the current page (non-link); ancestors are links."
      >
        <div className="sg-card">
          <Specimen label="Trail">
            <Breadcrumbs />
          </Specimen>
        </div>
      </Section>

      <Section
        id="nav-tabs"
        title="Tabs"
        desc="Switch facets within one resource. Roving tabindex — ←/→ moves selection, Home/End jump. Underline for in-panel sections; segmented for compact toggles."
      >
        <div className="sg-card">
          <Specimen label="Underline">
            <Tabs variant="underline" />
          </Specimen>
          <Specimen label="Segmented">
            <Tabs variant="segmented" />
          </Specimen>
        </div>
      </Section>

      <Section
        id="nav-palette"
        title="Command Palette ⭐"
        desc="The ⌘K launcher — one keystroke to any resource or action. Type to filter (matches highlighted), grouped results, full keyboard drive, per-row shortcut hints."
      >
        <div className="sg-card">
          <Specimen label="⌘K">
            <CommandPalette />
          </Specimen>
          <p className="sg-note">
            In product this opens as a centered modal over a dim scrim, input auto-focused. Typing
            filters live and re-groups; <code>↑</code>/<code>↓</code> move the selection (wrapping),
            <code>↵</code> runs it, <code>esc</code> dismisses. The input is a{" "}
            <code>role="combobox"</code> driving <code>aria-activedescendant</code> over a{" "}
            <code>role="listbox"</code>, so the highlighted row is announced without moving DOM
            focus off the field. Filled-glyph weight is reserved for the active row only.
          </p>
        </div>
      </Section>

      <Section
        id="nav-switcher"
        title="Quick Switcher"
        desc="A scoped, lighter palette — jump between recent runs/decisions/sessions. Live runs carry the amber dot; settled ones a teal check."
      >
        <div className="sg-card">
          <Specimen label="Switch to">
            <QuickSwitcher />
          </Specimen>
        </div>
      </Section>

      <Section
        id="nav-search"
        title="Search, filter & order"
        desc="The field filters the result set live as you type; status filters and the sort control compose on top. Matches are highlighted, with a live count and a designed empty state."
      >
        <div className="sg-card" style={{ display: "grid", gap: "var(--space-20)" }}>
          <Specimen label="search bar">
            <SearchBar />
          </Specimen>
          <Specimen label="search + filters + order">
            <SearchExplorer />
          </Specimen>
        </div>
      </Section>

      <Section
        id="nav-pagination"
        title="Pagination"
        desc="Page through long lists (sessions, decisions). Current page = tinted + accent border + bold + aria-current; ends disable the arrows."
      >
        <div className="sg-card">
          <Specimen label="Pages">
            <Pagination />
          </Specimen>
        </div>
      </Section>

      <Section
        id="nav-stepper"
        title="Stepper"
        desc="Linear progress through a multi-stage flow (the pipeline, or first-run setup). Done steps show a check, current is accent-ringed, upcoming muted."
      >
        <div className="sg-card">
          <Specimen label="Progress">
            <Stepper />
          </Specimen>
        </div>
      </Section>

      <Section
        id="nav-context"
        title="Context Menu"
        desc="Right-click actions on a resource: grouped by separators, each with its shortcut, one destructive item set apart. ↑↓ move, Enter activates, Esc closes."
      >
        <div className="sg-card">
          <Specimen label="Right-click">
            <ContextMenu />
          </Specimen>
        </div>
      </Section>
    </>
  );
}
