// Phase 3D · Data display — the styleguide gallery for ProductAgents' data
// surfaces (tables, lists, trees, badges, code/JSON, metric cards, timeline,
// diff, markdown). Built from the token layer only; every measured value is
// mono + tabular-nums; status pairs colour with a glyph + label. Adapts across
// both themes and both densities with zero markup change.
import { useState } from "react";
import type { CSSProperties, KeyboardEvent, ReactNode } from "react";
import { Section, Specimen } from "../sg";

/* ── tiny helpers ──────────────────────────────────────────────────────────── */

// Inline CSS custom-property style objects (TS needs the cast).
const vars = (o: Record<string, string>): CSSProperties => o as CSSProperties;

// Enter / Space activation for non-button interactive rows (keyboard-first).
const activate = (fn: () => void) => (e: KeyboardEvent) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    fn();
  }
};

const pct = (v: number) => `${Math.round(v * 100)}%`;
const confTier = (v: number) => (v < 0.5 ? "low" : v < 0.75 ? "medium" : "high");

/* ── Phosphor-style inline icons (SVG only, never emoji) ───────────────────── */

type IconName =
  | "chevron-right" | "chevron-down" | "sort" | "caret-up" | "caret-down"
  | "check" | "x" | "circle" | "warning" | "diamond" | "slash"
  | "copy" | "arrow-up" | "arrow-down" | "user"
  | "folder" | "file" | "database" | "plug" | "play";

const PATHS: Record<IconName, ReactNode> = {
  "chevron-right": <path d="M9 6l6 6-6 6" />,
  "chevron-down": <path d="M6 9l6 6 6-6" />,
  sort: <><path d="M8 10l4-4 4 4" /><path d="M8 14l4 4 4-4" /></>,
  "caret-up": <path d="M6 14l6-6 6 6" />,
  "caret-down": <path d="M6 10l6 6 6-6" />,
  check: <path d="M5 13l4 4L19 7" />,
  x: <path d="M6 6l12 12M18 6L6 18" />,
  circle: <circle cx="12" cy="12" r="7" />,
  warning: <><path d="M12 4l9 16H3z" /><path d="M12 10v4" /><path d="M12 17h.01" /></>,
  diamond: <path d="M12 3l9 9-9 9-9-9z" />,
  slash: <><circle cx="12" cy="12" r="8" /><path d="M7 7l10 10" /></>,
  copy: <><rect x="8" y="8" width="11" height="11" rx="2" /><path d="M16 8V6a2 2 0 00-2-2H6a2 2 0 00-2 2v8a2 2 0 002 2h2" /></>,
  "arrow-up": <path d="M12 19V5M6 11l6-6 6 6" />,
  "arrow-down": <path d="M12 5v14M6 13l6 6 6-6" />,
  user: <><circle cx="12" cy="9" r="3.5" /><path d="M5.5 20a6.5 6.5 0 0113 0" /></>,
  folder: <path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />,
  file: <><path d="M14 4H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V9z" /><path d="M14 4v5h5" /></>,
  database: <><ellipse cx="12" cy="6" rx="7" ry="3" /><path d="M5 6v12c0 1.66 3.13 3 7 3s7-1.34 7-3V6" /><path d="M5 12c0 1.66 3.13 3 7 3s7-1.34 7-3" /></>,
  plug: <><path d="M9 3v5M15 3v5" /><path d="M6 8h12v3a6 6 0 01-12 0z" /><path d="M12 17v4" /></>,
  play: <path d="M8 5l11 7-11 7z" />,
};

function Icon({ name, size = "sm" }: { name: IconName; size?: "xs" | "sm" | "md" | "lg" }) {
  return (
    <svg
      className={`dd-ico dd-ico--${size}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {PATHS[name]}
    </svg>
  );
}

/* ── Status badge — colour + glyph + label (WCAG 1.4.1) ────────────────────── */

type Status =
  | "done" | "running" | "waiting" | "degraded"
  | "failed" | "awaiting-human" | "cancelled";

const STATUS: Record<Status, { label: string; icon: IconName; fill: string; text: string; live?: boolean }> = {
  done:             { label: "Done",           icon: "check",   fill: "--ai-done",           text: "--ai-done-text" },
  running:          { label: "Running",        icon: "play",    fill: "--ai-running",        text: "--ai-running-text", live: true },
  waiting:          { label: "Waiting",        icon: "circle",  fill: "--ai-waiting",        text: "--text-secondary" },
  degraded:         { label: "Degraded",       icon: "warning", fill: "--ai-degraded",       text: "--ai-degraded-text" },
  failed:           { label: "Failed",         icon: "x",       fill: "--ai-failed",         text: "--ai-failed-text" },
  "awaiting-human": { label: "Awaiting human", icon: "diamond", fill: "--ai-awaiting-human", text: "--text-link" },
  cancelled:        { label: "Cancelled",      icon: "slash",   fill: "--ai-cancelled",      text: "--text-tertiary" },
};

function Badge({ status }: { status: Status }) {
  const c = STATUS[status];
  const style = vars({ "--dd-badge-fill": `var(${c.fill})`, "--dd-badge-text": `var(${c.text})` });
  return (
    <span className="dd-badge" data-live={c.live ? "true" : undefined} style={style}>
      {c.live ? <span className="dd-badge-pulse" aria-hidden="true" /> : <Icon name={c.icon} size="xs" />}
      <span>{c.label}</span>
    </span>
  );
}

/* ── Confidence — "measured quantity" gauge (signature motif) ──────────────── */

function ConfidenceMini({ value }: { value: number }) {
  const style = vars({ "--dd-conf-fill": `var(--ai-confidence-${confTier(value)})`, "--dd-conf-pct": pct(value) });
  return (
    <span className="dd-conf" style={style}>
      <span className="dd-conf-track"><span className="dd-conf-fill" /></span>
      <span className="dd-conf-val dd-num">{pct(value)}</span>
    </span>
  );
}

function ConfidenceBar({ value, label }: { value: number; label: string }) {
  const style = vars({ "--dd-conf-fill": `var(--ai-confidence-${confTier(value)})`, "--dd-conf-pct": pct(value) });
  return (
    <div className="dd-confbar" style={style}>
      <div className="dd-confbar-head">
        <span className="dd-confbar-label">{label}</span>
        <span className="dd-confbar-val dd-num">{pct(value)}</span>
      </div>
      <div className="dd-confbar-track"><span className="dd-confbar-fill" /></div>
    </div>
  );
}

/* ── Avatar — image / initials / fallback, three sizes ─────────────────────── */

// ponytail: placeholder sample portrait (data-URI, no network). Demo content,
// not a design token — like the lorem strings elsewhere in this gallery.
const PHOTO =
  "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='80' height='80'><rect width='80' height='80' fill='%23475569'/><circle cx='40' cy='31' r='14' fill='%23cbd5e1'/><rect x='15' y='50' width='50' height='30' rx='15' fill='%23cbd5e1'/></svg>";

function Avatar(props: {
  size?: "sm" | "md" | "lg";
  img?: string;
  initials?: string;
  fill?: string;
  label: string;
}) {
  const { size = "md", img, initials, fill, label } = props;
  const style = fill ? vars({ "--dd-avatar-fill": `var(${fill})` }) : undefined;
  return (
    <span className={`dd-avatar dd-avatar--${size}`} style={style} role="img" aria-label={label}>
      {img ? (
        <img className="dd-avatar-img" src={img} alt="" />
      ) : initials ? (
        <span className="dd-avatar-initials" aria-hidden="true">{initials}</span>
      ) : (
        <Icon name="user" size={size === "sm" ? "xs" : "sm"} />
      )}
    </span>
  );
}

/* ── Metric card (heavy-use) — big number + delta + trend ──────────────────── */

function Sparkline({ data }: { data: number[] }) {
  const w = 96, h = 28;
  const max = Math.max(...data), min = Math.min(...data);
  const span = max - min || 1;
  const points = data
    .map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / span) * (h - 4) - 2}`)
    .join(" ");
  return (
    <svg className="dd-spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" aria-hidden="true" focusable="false">
      <polyline points={points} fill="none" />
    </svg>
  );
}

function MetricCard(props: {
  label: string;
  value: string;
  delta: string;
  dir: "up" | "down";
  tone: "positive" | "negative" | "neutral";
  spark: number[];
}) {
  return (
    <div className="dd-stat">
      <div className="dd-stat-head">
        <span className="dd-stat-label">{props.label}</span>
        <Sparkline data={props.spark} />
      </div>
      <div className="dd-stat-value dd-num">{props.value}</div>
      <div className="dd-stat-delta" data-tone={props.tone}>
        <Icon name={props.dir === "up" ? "arrow-up" : "arrow-down"} size="xs" />
        <span className="dd-stat-delta-val dd-num">{props.delta}</span>
        <span className="dd-stat-delta-cap">vs. prior 5 runs</span>
      </div>
    </div>
  );
}

/* ── data ──────────────────────────────────────────────────────────────────── */

type DecisionRow = {
  id: string; title: string; confidence: number;
  tokens: number; cost: number; duration: number; status: Status;
};
const DECISIONS: DecisionRow[] = [
  { id: "dec-1042", title: "Adopt usage-based pricing tier", confidence: 0.82, tokens: 184230, cost: 2.47, duration: 312, status: "done" },
  { id: "dec-1041", title: "Sunset legacy mobile SDK v2", confidence: 0.64, tokens: 96120, cost: 1.18, duration: 204, status: "degraded" },
  { id: "dec-1040", title: "Prioritize SSO for enterprise", confidence: 0.91, tokens: 221540, cost: 3.02, duration: 358, status: "done" },
  { id: "dec-1039", title: "Launch AI changelog digest", confidence: 0.48, tokens: 54310, cost: 0.71, duration: 142, status: "failed" },
  { id: "dec-1038", title: "Expand to EU data residency", confidence: 0.73, tokens: 167890, cost: 2.21, duration: 297, status: "awaiting-human" },
];

type SortKey = "title" | "confidence" | "tokens" | "cost" | "duration";

const TIMELINE: { node: string; status: Status; time: string; dur: string; note: string }[] = [
  { node: "Evidence", status: "done", time: "14:22:01", dur: "4.2 s", note: "5 sources · 1,204 records" },
  { node: "Analyst team", status: "done", time: "14:22:05", dur: "38.6 s", note: "5 perspectives, parallel" },
  { node: "Debate", status: "done", time: "14:22:44", dur: "22.1 s", note: "2 rounds · advocate vs skeptic" },
  { node: "Strategist", status: "done", time: "14:23:06", dur: "11.8 s", note: "recommendation drafted" },
  { node: "Judge", status: "degraded", time: "14:23:18", dur: "6.4 s", note: "1 revision · grounding 0.71" },
  { node: "Risk", status: "running", time: "14:23:24", dur: "—", note: "evaluating 5 dimensions" },
  { node: "Governance", status: "waiting", time: "—", dur: "—", note: "awaiting risk" },
];

const FEED: { kind: "avatar" | "icon"; mark: string; fill: string; who: string; action: string; target: string; time: string }[] = [
  { kind: "avatar", mark: "MO", fill: "--ai-analyst-customer", who: "Maya Okonkwo", action: "recorded an outcome on", target: "dec-1037", time: "2 min ago" },
  { kind: "icon", mark: "plug", fill: "--ai-tool", who: "GitHub sync", action: "ingested", target: "42 issues", time: "11 min ago" },
  { kind: "avatar", mark: "RT", fill: "--ai-analyst-business", who: "Ravi Tan", action: "approved", target: "dec-1040", time: "38 min ago" },
  { kind: "icon", mark: "play", fill: "--ai-running", who: "Scheduler", action: "started run", target: "dec-1042", time: "1 hr ago" },
];

const DIFF: { o: string; n: string; t: "ctx" | "add" | "del"; text: string }[] = [
  { o: "12", n: "12", t: "ctx", text: "You are the Opportunity Skeptic." },
  { o: "13", n: "", t: "del", text: "Find every reason the initiative will fail." },
  { o: "", n: "13", t: "add", text: "Surface the strongest evidence-grounded risks." },
  { o: "", n: "14", t: "add", text: "Name the analyst report each risk derives from." },
  { o: "14", n: "15", t: "ctx", text: "Keep each point to a single sentence." },
];

const CODE = [
  "from productagents.platform import WorkflowService",
  "",
  'workflow = WorkflowService.for_model("anthropic:claude-sonnet-4-6")',
  "verdict = await workflow.evaluate_initiative(",
  '    "Prioritize SSO for enterprise",',
  '    evidence="sample",',
  ")",
  "print(verdict.confidence)  # 0.91",
];

const RUN_PARAMS: [string, string][] = [
  ["model", "anthropic:claude-sonnet-4-6"],
  ["debate_rounds", "2"],
  ["judge_threshold", "0.70"],
  ["max_retries", "6"],
  ["workspace", "default"],
];

/* ── JSON viewer (collapsible, tinted via text roles — not rainbow) ────────── */

type Json = string | number | boolean | null | Json[] | { [k: string]: Json };

const SAMPLE_JSON: Json = {
  id: "dec-1040",
  initiative: "Prioritize SSO for enterprise",
  status: "approved",
  confidence: 0.91,
  approved: true,
  evidence: ["customer_research", "product_analytics", "market", "business", "technical"],
  recommendation: { verdict: "proceed", risk: "medium", revisions: 1 },
};

function JsonLeaf({ value }: { value: string | number | boolean | null }) {
  if (value === null) return <span className="dd-json-null">null</span>;
  if (typeof value === "string") return <span className="dd-json-str">"{value}"</span>;
  if (typeof value === "number") return <span className="dd-json-num dd-num">{value}</span>;
  return <span className="dd-json-bool">{String(value)}</span>;
}

function JsonNode({ name, value, depth = 0 }: { name?: string; value: Json; depth?: number }) {
  const isContainer = value !== null && typeof value === "object";
  const [open, setOpen] = useState(depth < 1);
  const indent = vars({ "--dd-json-depth": String(depth) });

  if (!isContainer) {
    return (
      <div className="dd-json-row" style={indent}>
        {name !== undefined && <span className="dd-json-key">"{name}"</span>}
        {name !== undefined && <span className="dd-json-punc">:&nbsp;</span>}
        <JsonLeaf value={value as string | number | boolean | null} />
      </div>
    );
  }

  const isArr = Array.isArray(value);
  const entries: [string | undefined, Json][] = isArr
    ? (value as Json[]).map((v) => [undefined, v])
    : Object.entries(value as { [k: string]: Json });

  return (
    <div className="dd-json-branch">
      <button type="button" className="dd-json-toggle" style={indent} aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        <Icon name={open ? "chevron-down" : "chevron-right"} size="xs" />
        {name !== undefined && <span className="dd-json-key">"{name}"</span>}
        {name !== undefined && <span className="dd-json-punc">:&nbsp;</span>}
        <span className="dd-json-punc">{isArr ? "[" : "{"}</span>
        {!open && <span className="dd-json-count">{entries.length} {isArr ? "items" : "keys"}</span>}
        {!open && <span className="dd-json-punc">{isArr ? "]" : "}"}</span>}
      </button>
      {open && (
        <div className="dd-json-children">
          {entries.map(([k, v], i) => <JsonNode key={k ?? i} name={k} value={v} depth={depth + 1} />)}
        </div>
      )}
      {open && <div className="dd-json-punc dd-json-row" style={indent}>{isArr ? "]" : "}"}</div>}
    </div>
  );
}

/* ── Tree ──────────────────────────────────────────────────────────────────── */

type TreeItem = { id: string; label: string; icon: IconName; children?: TreeItem[] };
const TREE: TreeItem[] = [
  {
    id: "ws", label: "default workspace", icon: "folder", children: [
      {
        id: "decisions", label: "Decisions", icon: "folder", children: [
          { id: "d1040", label: "dec-1040 · Prioritize SSO", icon: "file" },
          { id: "d1039", label: "dec-1039 · AI changelog", icon: "file" },
        ],
      },
      {
        id: "connectors", label: "Connectors", icon: "folder", children: [
          { id: "github", label: "github · issues", icon: "plug" },
          { id: "jira", label: "jira · PROD board", icon: "plug" },
        ],
      },
      { id: "db", label: "productagents.db", icon: "database" },
    ],
  },
];

function TreeNode({ item, level, expanded, toggle }: {
  item: TreeItem; level: number; expanded: Set<string>; toggle: (id: string) => void;
}) {
  const hasChildren = !!item.children?.length;
  const isOpen = expanded.has(item.id);
  const style = vars({ "--dd-tree-level": String(level) });
  return (
    <li role="treeitem" aria-expanded={hasChildren ? isOpen : undefined} aria-level={level + 1}>
      <div
        className="dd-tree-row"
        tabIndex={0}
        style={style}
        onClick={() => hasChildren && toggle(item.id)}
        onKeyDown={activate(() => hasChildren && toggle(item.id))}
      >
        <span className="dd-tree-twist">
          {hasChildren ? <Icon name={isOpen ? "chevron-down" : "chevron-right"} size="xs" /> : null}
        </span>
        <Icon name={item.icon} size="sm" />
        <span className="dd-tree-label">{item.label}</span>
      </div>
      {hasChildren && isOpen && (
        <ul role="group" className="dd-tree-group">
          {item.children!.map((c) => (
            <TreeNode key={c.id} item={c} level={level + 1} expanded={expanded} toggle={toggle} />
          ))}
        </ul>
      )}
    </li>
  );
}

/* ── the gallery ───────────────────────────────────────────────────────────── */

export function Phase3DataDisplay() {
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({ key: "confidence", dir: "desc" });
  const [selected, setSelected] = useState("dec-1040");
  const [expanded, setExpanded] = useState<Set<string>>(new Set(["ws", "decisions"]));
  const [tags, setTags] = useState(["pricing", "enterprise", "q3-roadmap", "risk:medium"]);
  const [copied, setCopied] = useState(false);

  const toggleSort = (key: SortKey) =>
    setSort((s) => (s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: "asc" }));
  const toggleTree = (id: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  const copyCode = async () => {
    try { await navigator.clipboard.writeText(CODE.join("\n")); } catch { /* ponytail: clipboard may reject */ }
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  const sorted = [...DECISIONS].sort((a, b) => {
    const av = a[sort.key], bv = b[sort.key];
    const c = av < bv ? -1 : av > bv ? 1 : 0;
    return sort.dir === "asc" ? c : -c;
  });
  const ariaSort = (key: SortKey): "ascending" | "descending" | "none" =>
    sort.key === key ? (sort.dir === "asc" ? "ascending" : "descending") : "none";

  const NUM_COLS: { key: SortKey; label: string }[] = [
    { key: "confidence", label: "Confidence" },
    { key: "tokens", label: "Tokens" },
    { key: "cost", label: "Cost" },
    { key: "duration", label: "Duration" },
  ];

  return (
    <>
      <div className="sg-subband">
        <h3>3D · Data display</h3>
        <span>Tables, lists, trees, badges, code/JSON, metric cards, timeline, diff &amp; markdown — the surfaces that make a decision re-readable months later.</span>
      </div>

      {/* ── Metric cards (heavy-use) ──────────────────────────────────────── */}
      <Section id="dd-stats" title="Stat / metric cards" desc="Big mono readout + signed delta (arrow + sign) + trend sparkline. The numbers hold their columns (tabular figures).">
        <div className="sg-card">
          <div className="dd-stat-grid">
            <MetricCard label="Mean confidence" value="82%" delta="+6 pts" dir="up" tone="positive" spark={[58, 61, 60, 67, 72, 76, 82]} />
            <MetricCard label="Tokens / run" value="184,230" delta="+12%" dir="up" tone="neutral" spark={[120, 140, 132, 158, 166, 171, 184]} />
            <MetricCard label="Cost / run" value="$2.47" delta="−8%" dir="down" tone="positive" spark={[3.4, 3.1, 3.2, 2.9, 2.7, 2.6, 2.47]} />
            <MetricCard label="P50 latency" value="312 s" delta="+18 s" dir="up" tone="negative" spark={[260, 271, 268, 290, 301, 305, 312]} />
          </div>
        </div>
      </Section>

      {/* ── Table ─────────────────────────────────────────────────────────── */}
      <Section id="dd-table" title="Table" desc="Sortable headers (buttons + aria-sort), a selected row, numeric columns in tabular mono. Click a header to sort; click a row to select; rows are keyboard-focusable.">
        <div className="sg-card">
          <div className="dd-table-wrap">
            <table className="dd-table dd-table--zebra">
              <caption className="dd-sr-only">Recent decisions with confidence, token, cost, duration and status.</caption>
              <thead>
                <tr>
                  <th scope="col" aria-sort={ariaSort("title")}>
                    <button type="button" className="dd-th-sort" onClick={() => toggleSort("title")}>
                      Decision
                      <Icon name={sort.key === "title" ? (sort.dir === "asc" ? "caret-up" : "caret-down") : "sort"} size="xs" />
                    </button>
                  </th>
                  {NUM_COLS.map((col) => (
                    <th key={col.key} scope="col" className="dd-num-col" aria-sort={ariaSort(col.key)}>
                      <button type="button" className="dd-th-sort dd-th-sort--num" onClick={() => toggleSort(col.key)}>
                        <Icon name={sort.key === col.key ? (sort.dir === "asc" ? "caret-up" : "caret-down") : "sort"} size="xs" />
                        {col.label}
                      </button>
                    </th>
                  ))}
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((r) => (
                  <tr
                    key={r.id}
                    className="dd-tr"
                    aria-selected={selected === r.id}
                    tabIndex={0}
                    onClick={() => setSelected(r.id)}
                    onKeyDown={activate(() => setSelected(r.id))}
                  >
                    <th scope="row" className="dd-td-title">
                      <span className="dd-mono-id">{r.id}</span>
                      <span>{r.title}</span>
                    </th>
                    <td className="dd-num-col"><ConfidenceMini value={r.confidence} /></td>
                    <td className="dd-num-col dd-num">{r.tokens.toLocaleString()}</td>
                    <td className="dd-num-col dd-num">${r.cost.toFixed(2)}</td>
                    <td className="dd-num-col dd-num">{r.duration} s</td>
                    <td><Badge status={r.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Section>

      {/* ── Data grid ─────────────────────────────────────────────────────── */}
      <Section id="dd-grid" title="Data grid" desc="Denser than the table, with a column-resize affordance on each header edge (col-resize cursor). For synced records browsed at scale.">
        <div className="sg-card">
          <div className="dd-table-wrap">
            <table className="dd-table dd-grid">
              <thead>
                <tr>
                  {["Source", "Ref", "Sentiment", "Votes", "Synced"].map((h, i, a) => (
                    <th key={h} scope="col" className={i >= 3 ? "dd-num-col" : undefined}>
                      <span className="dd-grid-th">{h}</span>
                      {i < a.length - 1 && <span className="dd-grid-resize" aria-hidden="true" />}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  { src: "github", ref: "#482", sent: "positive", votes: 34, when: "14:21:08" },
                  { src: "github", ref: "#479", sent: "negative", votes: 12, when: "14:21:02" },
                  { src: "jira", ref: "PROD-318", sent: "neutral", votes: 7, when: "14:20:54" },
                  { src: "github", ref: "#471", sent: "positive", votes: 21, when: "14:20:41" },
                ].map((r) => (
                  <tr key={r.ref} className="dd-tr">
                    <td className="dd-mono-id">{r.src}</td>
                    <td className="dd-num">{r.ref}</td>
                    <td>
                      <span className="dd-tag dd-tag--sent" data-sent={r.sent}>
                        <Icon name={r.sent === "positive" ? "arrow-up" : r.sent === "negative" ? "arrow-down" : "circle"} size="xs" />
                        {r.sent}
                      </span>
                    </td>
                    <td className="dd-num-col dd-num">{r.votes}</td>
                    <td className="dd-num-col dd-num">{r.when}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Section>

      {/* ── List + Tree ───────────────────────────────────────────────────── */}
      <Section id="dd-list" title="List & tree" desc="Single- and multi-line list rows (leading icon + trailing meta) and a keyboard-operable resource tree.">
        <div className="sg-card dd-split">
          <div>
            <p className="dd-eyebrow">Multi-line list — sessions</p>
            <ul className="dd-list">
              {[
                { id: "s-3391", title: "Prioritize SSO for enterprise", sub: "5 analysts · 2 debate rounds · approved", status: "done" as Status, meta: "358 s" },
                { id: "s-3390", title: "Launch AI changelog digest", sub: "judge failed grounding gate", status: "failed" as Status, meta: "142 s" },
                { id: "s-3389", title: "Expand to EU data residency", sub: "paused at governance", status: "awaiting-human" as Status, meta: "297 s" },
              ].map((r) => (
                <li key={r.id} className="dd-list-row" tabIndex={0}>
                  <Icon name="file" size="md" />
                  <span className="dd-list-text">
                    <span className="dd-list-title">{r.title}</span>
                    <span className="dd-list-sub">{r.sub}</span>
                  </span>
                  <span className="dd-list-meta">
                    <span className="dd-num">{r.meta}</span>
                    <Badge status={r.status} />
                  </span>
                </li>
              ))}
            </ul>
            <p className="dd-eyebrow">Single-line list</p>
            <ul className="dd-list dd-list--single">
              {["evidence.collect", "analysts.fan_out", "debate.rounds", "strategist.draft"].map((t, i) => (
                <li key={t} className="dd-list-row" tabIndex={0}>
                  <Icon name="play" size="sm" />
                  <span className="dd-list-title dd-mono-id">{t}</span>
                  <span className="dd-list-meta dd-num">{[4.2, 38.6, 22.1, 11.8][i]} s</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="dd-eyebrow">Tree — workspace resources</p>
            <ul role="tree" aria-label="Workspace resources" className="dd-tree">
              {TREE.map((item) => (
                <TreeNode key={item.id} item={item} level={0} expanded={expanded} toggle={toggleTree} />
              ))}
            </ul>
          </div>
        </div>
      </Section>

      {/* ── Property list + Key/Value ─────────────────────────────────────── */}
      <Section id="dd-props" title="Property & key/value" desc="A description list of key→value pairs (decision metadata) and a compact key/value viewer (run parameters).">
        <div className="sg-card dd-split">
          <div>
            <p className="dd-eyebrow">Property list — dec-1040</p>
            <dl className="dd-props">
              <dt>ID</dt><dd className="dd-mono-id">dec-1040</dd>
              <dt>Initiative</dt><dd>Prioritize SSO for enterprise</dd>
              <dt>Owner</dt><dd className="dd-prop-owner"><Avatar size="sm" initials="RT" fill="--ai-analyst-business" label="Ravi Tan" /> Ravi Tan</dd>
              <dt>Status</dt><dd><Badge status="done" /></dd>
              <dt>Confidence</dt><dd className="dd-prop-conf"><ConfidenceBar value={0.91} label="grounding + coherence" /></dd>
              <dt>Model</dt><dd className="dd-num">anthropic:claude-sonnet-4-6</dd>
              <dt>Created</dt><dd className="dd-num">2026-06-28 14:23</dd>
            </dl>
          </div>
          <div>
            <p className="dd-eyebrow">Key / value — run parameters</p>
            <dl className="dd-kv">
              {RUN_PARAMS.map(([k, v]) => (
                <div className="dd-kv-row" key={k}>
                  <dt className="dd-kv-key">{k}</dt>
                  <dd className={`dd-kv-val dd-num ${/^[\d.]+$/.test(v) ? "dd-kv-val--num" : ""}`}>{v}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </Section>

      {/* ── Badges / tags / chips / avatars ───────────────────────────────── */}
      <Section id="dd-badges" title="Badges, tags, chips & avatars" desc="Status badges (colour + glyph + label), category tags, removable chips, and avatars (image / initials / fallback, three sizes).">
        <div className="sg-card">
          <Specimen label="status badges">
            {(Object.keys(STATUS) as Status[]).map((s) => <Badge key={s} status={s} />)}
          </Specimen>
          <Specimen label="tags">
            <span className="dd-tag">pricing</span>
            <span className="dd-tag">enterprise</span>
            <span className="dd-tag dd-tag--accent">risk: medium</span>
            <span className="dd-tag dd-tag--accent">q3-roadmap</span>
          </Specimen>
          <Specimen label="chips (removable)">
            {tags.length === 0 && <span className="dd-empty">all filters cleared</span>}
            {tags.map((t) => (
              <span className="dd-chip" key={t}>
                <span>{t}</span>
                <button
                  type="button"
                  className="dd-chip-x"
                  aria-label={`Remove ${t}`}
                  onClick={() => setTags((prev) => prev.filter((x) => x !== t))}
                >
                  <Icon name="x" size="xs" />
                </button>
              </span>
            ))}
          </Specimen>
          <Specimen label="avatar — kinds">
            <Avatar img={PHOTO} label="Synced portrait" />
            <Avatar initials="MO" fill="--ai-analyst-customer" label="Maya Okonkwo" />
            <Avatar label="Unknown actor" />
          </Specimen>
          <Specimen label="avatar — sizes">
            <Avatar size="sm" initials="RT" fill="--ai-analyst-business" label="Ravi Tan" />
            <Avatar size="md" initials="RT" fill="--ai-analyst-business" label="Ravi Tan" />
            <Avatar size="lg" initials="RT" fill="--ai-analyst-business" label="Ravi Tan" />
          </Specimen>
        </div>
      </Section>

      {/* ── Code block + JSON viewer ──────────────────────────────────────── */}
      <Section id="dd-code" title="Code block & JSON viewer" desc="Mono source with line numbers and a copy button; a collapsible JSON tree tinted via semantic text roles (keys, strings, numbers, booleans) — not a rainbow.">
        <div className="sg-card dd-split">
          <div>
            <p className="dd-eyebrow">Code block</p>
            <figure className="dd-code">
              <figcaption className="dd-code-bar">
                <span className="dd-mono-id">evaluate.py</span>
                <button type="button" className="dd-code-copy" onClick={copyCode} aria-live="polite">
                  <Icon name={copied ? "check" : "copy"} size="xs" />
                  {copied ? "Copied" : "Copy"}
                </button>
              </figcaption>
              <pre className="dd-code-pre"><code>
                {CODE.map((line, i) => (
                  <span className="dd-code-line" key={i}>
                    <span className="dd-code-gutter dd-num">{i + 1}</span>
                    <span className="dd-code-text">{line || " "}</span>
                  </span>
                ))}
              </code></pre>
            </figure>
          </div>
          <div>
            <p className="dd-eyebrow">JSON viewer</p>
            <div className="dd-json">
              <JsonNode value={SAMPLE_JSON} />
            </div>
          </div>
        </div>
      </Section>

      {/* ── Timeline + Activity feed ──────────────────────────────────────── */}
      <Section id="dd-timeline" title="Timeline & activity feed" desc="A vertical run timeline (node status + time + duration on a rail) and an activity feed of recent workspace actions. Amber = live; teal = settled.">
        <div className="sg-card dd-split">
          <div>
            <p className="dd-eyebrow">Run timeline</p>
            <ol className="dd-timeline">
              {TIMELINE.map((ev) => {
                const c = STATUS[ev.status];
                const style = vars({ "--dd-node-fill": `var(${c.fill})` });
                return (
                  <li className="dd-tl-row" key={ev.node} style={style} data-live={c.live ? "true" : undefined}>
                    <span className="dd-tl-marker" aria-hidden="true">
                      {c.live ? <span className="dd-badge-pulse" /> : <Icon name={c.icon} size="xs" />}
                    </span>
                    <div className="dd-tl-body">
                      <div className="dd-tl-head">
                        <span className="dd-tl-node">{ev.node}</span>
                        <Badge status={ev.status} />
                      </div>
                      <p className="dd-tl-note">{ev.note}</p>
                    </div>
                    <div className="dd-tl-meta dd-num">
                      <span>{ev.time}</span>
                      <span className="dd-tl-dur">{ev.dur}</span>
                    </div>
                  </li>
                );
              })}
            </ol>
          </div>
          <div>
            <p className="dd-eyebrow">Activity feed</p>
            <ul className="dd-feed">
              {FEED.map((f, i) => (
                <li className="dd-feed-row" key={i}>
                  {f.kind === "avatar"
                    ? <Avatar size="sm" initials={f.mark} fill={f.fill} label={f.who} />
                    : <span className="dd-feed-icon" style={vars({ "--dd-avatar-fill": `var(${f.fill})` })}><Icon name={f.mark as IconName} size="sm" /></span>}
                  <p className="dd-feed-text">
                    <b>{f.who}</b> {f.action} <span className="dd-mono-id">{f.target}</span>
                  </p>
                  <span className="dd-feed-time dd-num">{f.time}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Section>

      {/* ── Diff viewer + Markdown ────────────────────────────────────────── */}
      <Section id="dd-diff" title="Diff viewer & markdown" desc="Unified diff with +/− signs AND tints (never colour alone) — a prompt-registry version change. Plus a styled markdown renderer.">
        <div className="sg-card dd-split">
          <div>
            <p className="dd-eyebrow">Diff — skeptic.txt v3 → v4</p>
            <div className="dd-diff" role="table" aria-label="Unified diff">
              {DIFF.map((d, i) => (
                <div className={`dd-diff-line dd-diff-line--${d.t}`} role="row" key={i}>
                  <span className="dd-diff-ln dd-num" role="cell">{d.o}</span>
                  <span className="dd-diff-ln dd-num" role="cell">{d.n}</span>
                  <span className="dd-diff-sign" role="cell" aria-hidden="true">{d.t === "add" ? "+" : d.t === "del" ? "−" : " "}</span>
                  <span className="dd-diff-text" role="cell">{d.text}</span>
                </div>
              ))}
            </div>
          </div>
          <div>
            <p className="dd-eyebrow">Markdown renderer</p>
            <div className="dd-md">
              <h2>Recommendation</h2>
              <p>Proceed with <strong>SSO for enterprise</strong>, scoped to the top-20 accounts by ARR. Confidence is <code>0.91</code> after one strategist revision.</p>
              <h3>Why now</h3>
              <ul>
                <li>34 upvoted requests in the last quarter</li>
                <li>Two churned accounts cited the gap</li>
              </ul>
              <blockquote>The market analyst flags SAML parity as table-stakes for the segment.</blockquote>
              <p>See <a href="#dd-table">the decision table</a> for the full run.</p>
            </div>
          </div>
        </div>
      </Section>
    </>
  );
}
