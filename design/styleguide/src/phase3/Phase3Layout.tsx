import type React from "react";
import { Section, Specimen } from "../sg";

/* ── Phosphor-style inline SVG icons (never emoji). `fill` weight is reserved
 *    for the single active/selected item, per the iconography token contract. */
function Svg(props: { children: React.ReactNode; size?: "xs" | "sm" | "md"; filled?: boolean }) {
  const { children, size = "sm", filled = false } = props;
  return (
    <svg
      className={`la-ico la-ico--${size}`}
      viewBox="0 0 24 24"
      fill={filled ? "currentColor" : "none"}
      stroke={filled ? "none" : "currentColor"}
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

/* Outline + filled (active) glyph for each real ProductAgents resource. */
const RES_ICON: Record<string, (filled: boolean) => React.ReactNode> = {
  run: (f) => <Svg filled={f}>{f ? <path d="M8 5.2v13.6L19 12 8 5.2Z" /> : <path d="M8 5.2v13.6L19 12 8 5.2Z" />}</Svg>,
  workflows: (f) => (
    <Svg filled={f}>
      <circle cx="6" cy="6" r="2.4" />
      <circle cx="18" cy="6" r="2.4" />
      <circle cx="12" cy="18" r="2.4" />
      <path d="M7.6 7.7 11 15.6M16.4 7.7 13 15.6" />
    </Svg>
  ),
  sessions: (f) => (
    <Svg filled={f}>
      <circle cx="12" cy="12" r="8.2" />
      <path d="M12 7.6V12l3 1.8" />
    </Svg>
  ),
  decisions: (f) => (
    <Svg filled={f}>
      <circle cx="6.5" cy="5" r="2" />
      <circle cx="6.5" cy="19" r="2" />
      <circle cx="17.5" cy="8" r="2" />
      <path d="M6.5 7v10M8.4 7.6c.4 5 9.1 1.7 9.1 8.4" />
    </Svg>
  ),
  connectors: (f) => (
    <Svg filled={f}>
      <path d="M9 7.5V3M15 7.5V3M7.5 7.5h9v3.5a4.5 4.5 0 0 1-9 0V7.5ZM12 16v5" />
    </Svg>
  ),
  prompts: (f) => (
    <Svg filled={f}>
      <rect x="4" y="5.5" width="16" height="13" rx="1.5" />
      <path d="M8 10.5l2.2 2-2.2 2M13 14.5h3" />
    </Svg>
  ),
  settings: (f) => (
    <Svg filled={f}>
      <path d="M4 8h9M19 8h1M4 16h1M11 16h9" />
      <circle cx="15" cy="8" r="2.2" />
      <circle cx="7" cy="16" r="2.2" />
    </Svg>
  ),
};

type Resource = { id: string; label: string };
const RESOURCES: Resource[] = [
  { id: "run", label: "Run" },
  { id: "workflows", label: "Workflows" },
  { id: "sessions", label: "Sessions" },
  { id: "decisions", label: "Decisions" },
  { id: "connectors", label: "Connectors" },
  { id: "prompts", label: "Prompts" },
  { id: "settings", label: "Settings" },
];

/* Small generic glyphs used in the chrome. */
const SearchIcon = () => (
  <Svg size="xs">
    <circle cx="11" cy="11" r="7" />
    <path d="M21 21l-4.3-4.3" />
  </Svg>
);
const PlusIcon = () => (
  <Svg size="xs">
    <path d="M12 5v14M5 12h14" />
  </Svg>
);

/** The resource navigation sidebar — the real ProductAgents resource list.
 *  `active` gets the filled glyph, the accent marker, and aria-current. */
function NavSidebar({ active = "run", collapsed = false }: { active?: string; collapsed?: boolean }) {
  return (
    <nav className={`la-rail${collapsed ? " la-rail--collapsed" : ""}`} aria-label="Resources">
      {!collapsed && <div className="la-rail-head">Workspace · default</div>}
      <ul className="la-nav">
        {RESOURCES.map((r) => {
          const isActive = r.id === active;
          return (
            <li key={r.id}>
              <a
                href="#0"
                className={`la-nav-item${isActive ? " is-active" : ""}`}
                aria-current={isActive ? "page" : undefined}
                title={collapsed ? r.label : undefined}
              >
                <span className="la-nav-marker" aria-hidden="true" />
                {RES_ICON[r.id](isActive)}
                {!collapsed && <span className="la-nav-label">{r.label}</span>}
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

/** Window frame title bar — the OS chrome region (Tauri). */
function TitleBar() {
  return (
    <header className="la-titlebar">
      <span className="la-titlebar-title">ProductAgents</span>
      <span className="la-titlebar-sub">an IDE for decision-making</span>
      <span className="la-titlebar-spacer" />
      <div className="la-win-controls" role="group" aria-label="Window controls">
        <button type="button" className="la-win-btn" aria-label="Minimize">
          <Svg size="xs">
            <path d="M5 12h14" />
          </Svg>
        </button>
        <button type="button" className="la-win-btn" aria-label="Maximize">
          <Svg size="xs">
            <rect x="6" y="6" width="12" height="12" rx="1.5" />
          </Svg>
        </button>
        <button type="button" className="la-win-btn la-win-btn--close" aria-label="Close">
          <Svg size="xs">
            <path d="M6.5 6.5l11 11M17.5 6.5l-11 11" />
          </Svg>
        </button>
      </div>
    </header>
  );
}

/** Top bar — breadcrumb context + global search + primary action. */
function TopBar() {
  return (
    <div className="la-topbar">
      <nav className="la-crumbs" aria-label="Breadcrumb">
        <a href="#0">Run</a>
        <span className="la-crumb-sep" aria-hidden="true">
          /
        </span>
        <span aria-current="page">evaluate_initiative</span>
      </nav>
      <span className="la-topbar-spacer" />
      <div className="la-search" role="search">
        <SearchIcon />
        <input type="search" placeholder="Search runs…" aria-label="Search runs" />
        <kbd className="la-kbd">⌘K</kbd>
      </div>
      <button type="button" className="demo-btn demo-btn--primary la-topbar-action">
        <PlusIcon />
        New Run
      </button>
    </div>
  );
}

/** Context toolbar — view tabs + a live status pill for the current resource. */
function ContextToolbar() {
  const tabs = ["Timeline", "Evidence", "Debate", "Decision"];
  return (
    <div className="la-toolbar">
      <div className="la-tabs" role="tablist" aria-label="Run views">
        {tabs.map((t, i) => (
          <button key={t} type="button" role="tab" aria-selected={i === 0} className={`la-tab${i === 0 ? " is-active" : ""}`}>
            {t}
          </button>
        ))}
      </div>
      <span className="la-topbar-spacer" />
      {/* Live signal = amber + animated dot + glyph + label (color is never the only channel). */}
      <span className="la-runpill">
        <span className="la-runpill-dot" data-live="true" aria-hidden="true" />
        Running · node 4 / 9
      </span>
    </div>
  );
}

/** Right-hand inspector — key/value detail for the selected resource. */
function Inspector() {
  const rows: [string, string][] = [
    ["Status", "running"],
    ["Workflow", "evaluate_initiative"],
    ["Model", "sonnet-4-6"],
    ["Started", "14:02:11"],
    ["Confidence", "0.74"],
  ];
  return (
    <aside className="la-inspector" aria-label="Inspector">
      <div className="la-inspector-head">Inspector</div>
      <dl className="la-kv">
        {rows.map(([k, v]) => (
          <div className="la-kv-row" key={k}>
            <dt>{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>
    </aside>
  );
}

/** The centerpiece: a small but real app-shell composition. */
function AppShell() {
  return (
    <div className="la-shell" role="group" aria-label="Application shell preview">
      <TitleBar />
      <div className="la-shell-body">
        <NavSidebar active="run" />
        <main className="la-main">
          <TopBar />
          <ContextToolbar />
          <div className="la-content la-scroll">
            <div className="la-page">
              <div className="la-prim-section">
                <h4 className="la-prim-section-title">Reasoning timeline</h4>
                <p className="la-prim-section-desc">Live execution of the advisory pipeline.</p>
              </div>
              <div className="la-card la-card--raised">
                <div className="la-card-head">
                  <span>Customer Research</span>
                  <span className="la-card-meta">done</span>
                </div>
                <div className="la-card-body">3 feedback themes weighted; churn signal corroborated by analytics.</div>
              </div>
              <div className="la-card">
                <div className="la-card-head">
                  <span>Strategist</span>
                  <span className="la-card-meta">running</span>
                </div>
                <div className="la-card-body">Synthesising the debate transcript against recalled lessons…</div>
              </div>
            </div>
          </div>
        </main>
        <Inspector />
      </div>
    </div>
  );
}

export function Phase3Layout() {
  return (
    <>
      <div className="sg-subband">
        <h3>3A · Layout</h3>
        <span>App shell, panels, and surfaces — the structural frame the rest sits inside.</span>
      </div>

      <Section
        id="la-shell"
        title="App Shell"
        desc="The centerpiece composition: window frame, resource sidebar, top bar, context toolbar, main, and inspector — the resource-explorer IA, built from tokens only."
      >
        <div className="sg-card">
          <AppShell />
        </div>
      </Section>

      <Section id="la-regions" title="Shell regions" desc="Each region of the shell as a standalone, labelled specimen.">
        <div className="sg-card">
          <Specimen label="window frame">
            <div className="la-region-box la-region-box--wide">
              <TitleBar />
            </div>
          </Specimen>
          <Specimen label="top bar">
            <div className="la-region-box la-region-box--wide">
              <TopBar />
            </div>
          </Specimen>
          <Specimen label="context toolbar">
            <div className="la-region-box la-region-box--wide">
              <ContextToolbar />
            </div>
          </Specimen>
          <Specimen label="navigation sidebar">
            <div className="la-region-box la-region-box--rail">
              <NavSidebar active="decisions" />
            </div>
          </Specimen>
          <Specimen label="sidebar · collapsed rail">
            <div className="la-region-box la-region-box--rail-collapsed">
              <NavSidebar active="decisions" collapsed />
            </div>
          </Specimen>
          <Specimen label="secondary sidebar">
            <div className="la-region-box la-region-box--rail">
              <nav className="la-rail la-rail--secondary" aria-label="Sessions">
                <div className="la-rail-head">Recent sessions</div>
                <ul className="la-nav">
                  {["#a91c · evaluate", "#a90f · pricing", "#a8e2 · churn"].map((s, i) => (
                    <li key={s}>
                      <a href="#0" className={`la-nav-item${i === 0 ? " is-active" : ""}`} aria-current={i === 0 ? "page" : undefined}>
                        <span className="la-nav-marker" aria-hidden="true" />
                        <span className="la-nav-label la-nav-label--mono">{s}</span>
                      </a>
                    </li>
                  ))}
                </ul>
              </nav>
            </div>
          </Specimen>
          <Specimen label="inspector panel">
            <div className="la-region-box la-region-box--inspector">
              <Inspector />
            </div>
          </Specimen>
        </div>
      </Section>

      <Section
        id="la-panels"
        title="Panels — split, resizable, docked"
        desc="Multi-pane layouts with a real resize-handle affordance (col-resize cursor, keyboard-focusable separator)."
      >
        <div className="sg-card">
          <Specimen label="split · resizable">
            <div className="la-split">
              <div className="la-pane">
                <div className="la-pane-head">Evidence</div>
                <p className="la-pane-body">Five synced sources, weighted by recency.</p>
              </div>
              <div className="la-resize" role="separator" aria-orientation="vertical" aria-label="Resize panels" tabIndex={0}>
                <span className="la-resize-grip" aria-hidden="true" />
              </div>
              <div className="la-pane">
                <div className="la-pane-head">Detail</div>
                <p className="la-pane-body">Drag the handle (col-resize) to retitle column widths.</p>
              </div>
            </div>
          </Specimen>
          <Specimen label="docked panel">
            <div className="la-dock">
              <div className="la-dock-main">Main editor area</div>
              <div className="la-dock-panel">
                <div className="la-dock-tabs" role="tablist" aria-label="Docked panels">
                  <button type="button" role="tab" aria-selected="true" className="la-dock-tab is-active">
                    Logs
                  </button>
                  <button type="button" role="tab" aria-selected="false" className="la-dock-tab">
                    Problems
                  </button>
                </div>
                <div className="la-dock-body">Docked at the bottom edge — collapsible, like a terminal panel.</div>
              </div>
            </div>
          </Specimen>
        </div>
      </Section>

      <Section
        id="la-primitives"
        title="Layout primitives"
        desc="Workspace, page container, the Section primitive, surfaces, and dividers — the structural atoms the regions are built from."
      >
        <div className="sg-card">
          <Specimen label="workspace + page">
            <div className="la-workspace">
              <div className="la-page la-page--demo">
                <div className="la-prim-section">
                  <h4 className="la-prim-section-title">Page container</h4>
                  <p className="la-prim-section-desc">Width-capped, page-padded reading column inside the workspace canvas.</p>
                </div>
              </div>
            </div>
          </Specimen>
          <Specimen label="surface · default / raised / sunken">
            <div className="la-surface la-surface--default">default</div>
            <div className="la-surface la-surface--raised">raised</div>
            <div className="la-surface la-surface--sunken">sunken</div>
          </Specimen>
          <Specimen label="divider · horizontal">
            <div className="la-divider-demo">
              <span>Section A</span>
              <hr className="la-divider" />
              <span>Section B</span>
            </div>
          </Specimen>
          <Specimen label="divider · vertical">
            <div className="la-vdivider-demo">
              <span>Run</span>
              <span className="la-divider la-divider--v" role="separator" aria-orientation="vertical" />
              <span>Sessions</span>
              <span className="la-divider la-divider--v" role="separator" aria-orientation="vertical" />
              <span>Decisions</span>
            </div>
          </Specimen>
        </div>
      </Section>

      <Section id="la-card" title="Card" desc="The default content container — with/without header, default vs raised elevation.">
        <div className="sg-card">
          <Specimen label="default · headerless">
            <div className="la-card la-card--demo">
              <div className="la-card-body">A plain card resting on the canvas. Subtle border, no shadow.</div>
            </div>
          </Specimen>
          <Specimen label="default · with header">
            <div className="la-card la-card--demo">
              <div className="la-card-head">
                <span>Recommendation</span>
                <span className="la-card-meta">v3</span>
              </div>
              <div className="la-card-body">Header divider separates the title row from the body.</div>
            </div>
          </Specimen>
          <Specimen label="raised · with header">
            <div className="la-card la-card--raised la-card--demo">
              <div className="la-card-head">
                <span>Final verdict</span>
                <span className="la-card-meta">approved</span>
              </div>
              <div className="la-card-body">Raised surface + resting shadow lift it above sibling cards.</div>
            </div>
          </Specimen>
        </div>
      </Section>

      <Section id="la-scroll" title="Scroll area" desc="An overflow region with a styled, unobtrusive scrollbar (thin track, pill thumb).">
        <div className="sg-card">
          <Specimen label="vertical overflow">
            <div className="la-scroll la-scroll--demo">
              {Array.from({ length: 14 }, (_, i) => (
                <div className="la-scroll-row" key={i}>
                  <span className="la-scroll-row-idx">{String(i + 1).padStart(2, "0")}</span>
                  <span>span event · node.{i + 1} · {(120 + i * 37) % 1000}ms</span>
                </div>
              ))}
            </div>
          </Specimen>
        </div>
      </Section>
    </>
  );
}
