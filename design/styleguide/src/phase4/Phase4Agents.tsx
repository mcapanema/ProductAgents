// Phase 4A — Agent Components gallery.
// StatusBadge, AgentCard, Profile, CapabilityList, Selector, Timeline, Queue,
// DependencyGraph — the UI vocabulary for showing AI agent state and pipeline
// structure. Built from the token layer only (--ai-* tokens for all AI state).
import { useState } from "react";
import type { CSSProperties } from "react";
import { Section, Specimen } from "../sg";
import "./phase4a-agents.css";

/* ── helpers ───────────────────────────────────────────────────────────────── */

// Cast a record to CSSProperties so TS accepts CSS custom-property assignments.
const vars = (o: Record<string, string>): CSSProperties => o as CSSProperties;

/* ── Inline SVG icons (Phosphor-style: 24-grid, currentColor stroke) ─────── */

type IconName =
  | "check" | "circle" | "clock" | "x" | "warning" | "slash"
  | "diamond" | "play" | "search" | "brain" | "chart" | "users"
  | "globe" | "briefcase" | "code" | "database" | "plug" | "book"
  | "sparkle" | "scale" | "shield" | "funnel";

const PATHS: Record<IconName, React.ReactNode> = {
  check:     <path d="M5 13l4 4L19 7" />,
  circle:    <circle cx="12" cy="12" r="7" fill="none" />,
  clock:     <><circle cx="12" cy="12" r="8" /><path d="M12 8v4l2.5 2.5" /></>,
  x:         <path d="M6 6l12 12M18 6L6 18" />,
  warning:   <><path d="M12 4l9 16H3z" /><path d="M12 10v4" /><path d="M12 17h.01" /></>,
  slash:     <><circle cx="12" cy="12" r="8" /><path d="M7 7l10 10" /></>,
  diamond:   <path d="M12 3l9 9-9 9-9-9z" />,
  play:      <path d="M8 5l11 7-11 7z" />,
  search:    <><circle cx="10.5" cy="10.5" r="6.5" /><path d="M15.5 15.5l4 4" /></>,
  brain:     <path d="M9 3c-2.8.4-5 2.9-5 5.7 0 1.7.7 3.2 1.8 4.3H5v2h7v-2h.2C16.7 11.7 18 9.5 18 7 18 4.2 15.8 2 13 2c-.8 0-1.5.2-2.2.5A5 5 0 009 3z" />,
  chart:     <><path d="M3 20h18M6 20V14m4 6V8m4 12V4m4 16v-6" /></>,
  users:     <><circle cx="8" cy="9" r="3.5" /><path d="M2 20a6 6 0 0112 0" /><circle cx="17" cy="9" r="3" /><path d="M22 20a5 5 0 00-8-3.5" /></>,
  globe:     <><circle cx="12" cy="12" r="9" /><path d="M2 12h20M12 3a15 15 0 010 18M12 3a15 15 0 000 18" /></>,
  briefcase: <><rect x="2" y="9" width="20" height="12" rx="2" /><path d="M16 9V7a4 4 0 00-8 0v2" /><path d="M12 14v2" /></>,
  code:      <><path d="M8 9l-3 3 3 3" /><path d="M16 9l3 3-3 3" /><path d="M14 6l-4 12" /></>,
  database:  <><ellipse cx="12" cy="6" rx="7" ry="3" /><path d="M5 6v12c0 1.66 3.13 3 7 3s7-1.34 7-3V6" /><path d="M5 12c0 1.66 3.13 3 7 3s7-1.34 7-3" /></>,
  plug:      <><path d="M9 3v5M15 3v5" /><path d="M6 8h12v3a6 6 0 01-12 0z" /><path d="M12 17v4" /></>,
  book:      <><path d="M4 19.5A2.5 2.5 0 016.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" /></>,
  sparkle:   <path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z" />,
  scale:     <><path d="M12 3v18M3 8l9-5 9 5" /><path d="M6 12l-3 6h6z" /><path d="M18 12l-3 6h6z" /></>,
  shield:    <path d="M12 3l8 3.5V12c0 5-8 9-8 9s-8-4-8-9V6.5z" />,
  funnel:    <path d="M3 4h18l-7 9v6l-4-2V13z" />,
};

function Icon({ name, size = "xs" }: { name: IconName; size?: "xs" | "sm" | "md" }) {
  return (
    <svg
      className={`p4a-ico p4a-ico--${size}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {PATHS[name]}
    </svg>
  );
}

/* ── Types ──────────────────────────────────────────────────────────────────── */

type AgentStatus =
  | "waiting" | "running" | "done" | "degraded"
  | "failed" | "awaiting-human" | "cancelled";

type Priority = "high" | "medium" | "low";

/* ── Status config table ────────────────────────────────────────────────────── */

const STATUS_CFG: Record<AgentStatus, {
  label: string;
  icon: IconName;
  fill: string;       // --ai-* token name
  text: string;       // --ai-*-text token name
  live?: boolean;
}> = {
  waiting:          { label: "Waiting",         icon: "circle",  fill: "--ai-waiting",        text: "--text-secondary" },
  running:          { label: "Running",         icon: "play",    fill: "--ai-running",        text: "--ai-running-text", live: true },
  done:             { label: "Done",            icon: "check",   fill: "--ai-done",           text: "--ai-done-text" },
  degraded:         { label: "Degraded",        icon: "warning", fill: "--ai-degraded",       text: "--ai-degraded-text" },
  failed:           { label: "Failed",          icon: "x",       fill: "--ai-failed",         text: "--ai-failed-text" },
  "awaiting-human": { label: "Awaiting human",  icon: "diamond", fill: "--ai-awaiting-human", text: "--text-link" },
  cancelled:        { label: "Cancelled",       icon: "slash",   fill: "--ai-cancelled",      text: "--text-tertiary" },
};

/* ═══════════════════════════════════════════════════════ 1. STATUS BADGE ═══ */

function StatusBadge({ status }: { status: AgentStatus }) {
  const cfg = STATUS_CFG[status];
  const style = vars({ "--p4a-badge-fill": `var(${cfg.fill})`, "--p4a-badge-text": `var(${cfg.text})` });
  return (
    <span className="p4a-status-badge" style={style}>
      {cfg.live
        ? <span className="p4a-status-badge__dot" aria-hidden="true" />
        : <span className="p4a-status-badge__icon"><Icon name={cfg.icon} size="xs" /></span>
      }
      {cfg.label}
    </span>
  );
}

/* ═══════════════════════════════════════════════════════ 2. AGENT CARD ═══ */

type AgentDef = {
  id: string;
  name: string;
  role: string;
  desc: string;
  status: AgentStatus;
  confidence: number;
  colorVar: string;    // --ai-analyst-* token
  icon: IconName;
};

const AGENTS: AgentDef[] = [
  { id: "customer",  name: "Customer",   role: "customer_research",   desc: "Ingests synced feedback, surfaces voiced needs.",          status: "done",     confidence: 0.87, colorVar: "--ai-analyst-customer",  icon: "users"     },
  { id: "analytics", name: "Analytics",  role: "product_analytics",   desc: "Reads product metrics and usage cohorts.",                 status: "done",     confidence: 0.79, colorVar: "--ai-analyst-analytics", icon: "chart"     },
  { id: "market",    name: "Market",     role: "market",              desc: "Frames competitive landscape and market timing.",          status: "running",  confidence: 0,    colorVar: "--ai-analyst-market",    icon: "globe"     },
  { id: "business",  name: "Business",   role: "business",            desc: "Models revenue, cost and strategic alignment.",           status: "waiting",  confidence: 0,    colorVar: "--ai-analyst-business",  icon: "briefcase" },
  { id: "technical", name: "Technical",  role: "technical",           desc: "Assesses feasibility, debt and implementation risk.",      status: "waiting",  confidence: 0,    colorVar: "--ai-analyst-technical", icon: "code"      },
  { id: "strategist",name: "Strategist", role: "strategist",          desc: "Synthesises all reports into a governed recommendation.",  status: "waiting",  confidence: 0,    colorVar: "--accent",               icon: "sparkle"   },
];

function AgentCard({ agent, selected, onSelect }: { agent: AgentDef; selected: boolean; onSelect: () => void }) {
  const pct = agent.confidence > 0 ? `${Math.round(agent.confidence * 100)}%` : "—";
  const tier = agent.confidence < 0.5 ? "low" : agent.confidence < 0.75 ? "medium" : "high";
  const style = vars({
    "--p4a-agent-color": `var(${agent.colorVar})`,
    "--p4a-conf-fill": `var(--ai-confidence-${tier})`,
    "--p4a-conf-pct": pct === "—" ? "0%" : pct,
  });
  return (
    <div
      className="p4a-agent-card"
      style={style}
      role="option"
      aria-selected={selected}
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(); } }}
    >
      <div className="p4a-agent-card__head">
        <span className="p4a-agent-card__avatar">
          <Icon name={agent.icon} size="sm" />
        </span>
        <StatusBadge status={agent.status} />
      </div>
      <div>
        <p className="p4a-agent-card__name">{agent.name}</p>
        <p className="p4a-agent-card__role">{agent.role}</p>
        <p className="p4a-agent-card__body">{agent.desc}</p>
      </div>
      <div className="p4a-agent-card__foot">
        {agent.confidence > 0 ? (
          <span className="p4a-agent-card__conf">
            <span className="p4a-agent-card__conf-track">
              <span className="p4a-agent-card__conf-fill" />
            </span>
            <span className="p4a-agent-card__conf-val">{pct}</span>
          </span>
        ) : (
          <span className="p4a-agent-card__conf-val" style={{ color: "var(--text-tertiary)" }}>—</span>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════ 3. PROFILE ═══ */

function AgentProfile({ agent }: { agent: AgentDef }) {
  const style = vars({ "--p4a-agent-color": `var(${agent.colorVar})` });
  return (
    <div className="p4a-profile" style={style}>
      <div className="p4a-profile__avatar" aria-hidden="true">
        <Icon name={agent.icon} size="md" />
      </div>
      <div className="p4a-profile__body">
        <div className="p4a-profile__head">
          <div>
            <h4 className="p4a-profile__name">{agent.name} analyst</h4>
            <p className="p4a-profile__role">{agent.role} · node 3 of 11</p>
          </div>
          <StatusBadge status={agent.status} />
        </div>
        <p className="p4a-profile__desc">
          {agent.desc} This analyst reads evidence from the local canonical store and synced connectors, degrades gracefully to scenario evidence when the store is empty.
        </p>
        <div className="p4a-profile__stats">
          <div className="p4a-profile__stat">
            <span className="p4a-profile__stat-val">0.87</span>
            <span className="p4a-profile__stat-label">Confidence</span>
          </div>
          <div className="p4a-profile__stat">
            <span className="p4a-profile__stat-val">38.4 s</span>
            <span className="p4a-profile__stat-label">Duration</span>
          </div>
          <div className="p4a-profile__stat">
            <span className="p4a-profile__stat-val">18,340</span>
            <span className="p4a-profile__stat-label">Tokens</span>
          </div>
          <div className="p4a-profile__stat">
            <span className="p4a-profile__stat-val">$0.21</span>
            <span className="p4a-profile__stat-label">Cost</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════ 4. CAPABILITY LIST ═══ */

type Capability = { name: string; desc: string; tag: string; icon: IconName; colorVar: string };

const CAPABILITIES: Capability[] = [
  { name: "Semantic retrieval",     desc: "Hybrid lexical + cosine search over the DecisionStore.",    tag: "memory",    icon: "database",  colorVar: "--ai-thinking" },
  { name: "Connector sync",         desc: "Pull issues from GitHub and Jira into CustomerFeedback.",   tag: "connector", icon: "plug",      colorVar: "--ai-tool" },
  { name: "Structured output",      desc: "Returns typed schemas via function-calling; never raw text.", tag: "model",  icon: "code",      colorVar: "--ai-analyst-analytics" },
  { name: "Evidence collection",    desc: "Resolves scenario names, directory paths, or store live.",  tag: "evidence",  icon: "funnel",    colorVar: "--ai-analyst-customer" },
  { name: "Prompt versioning",      desc: "Reads workspace overrides from the PromptStore.",           tag: "registry",  icon: "book",      colorVar: "--ai-analyst-business" },
  { name: "Human-in-the-loop",      desc: "Pauses at governance for an approval decision.",            tag: "HITL",      icon: "shield",    colorVar: "--ai-awaiting-human" },
];

function CapabilityList({ items }: { items: Capability[] }) {
  return (
    <ul className="p4a-cap-list" role="list">
      {items.map((cap) => (
        <li key={cap.name} className="p4a-cap-item" style={vars({ "--p4a-cap-color": `var(${cap.colorVar})` })}>
          <span className="p4a-cap-item__icon">
            <Icon name={cap.icon} size="xs" />
          </span>
          <span className="p4a-cap-item__text">
            <span className="p4a-cap-item__name">{cap.name}</span>
            <span className="p4a-cap-item__desc">{cap.desc}</span>
          </span>
          <span className="p4a-cap-item__tag">{cap.tag}</span>
        </li>
      ))}
    </ul>
  );
}

/* ═══════════════════════════════════════════════════════ 5. SELECTOR ═══ */

type SelectorItem = { id: string; name: string; meta: string; icon: IconName; colorVar: string };

const SELECTOR_ITEMS: SelectorItem[] = [
  { id: "customer",   name: "Customer research",  meta: "feedback · issues · NPS",        icon: "users",     colorVar: "--ai-analyst-customer"  },
  { id: "analytics",  name: "Product analytics",  meta: "metrics · cohorts · retention",  icon: "chart",     colorVar: "--ai-analyst-analytics" },
  { id: "market",     name: "Market",             meta: "competition · timing · TAM",     icon: "globe",     colorVar: "--ai-analyst-market"    },
  { id: "business",   name: "Business",           meta: "revenue · cost · strategy",      icon: "briefcase", colorVar: "--ai-analyst-business"  },
  { id: "technical",  name: "Technical",          meta: "feasibility · debt · risk",      icon: "code",      colorVar: "--ai-analyst-technical" },
  { id: "strategist", name: "Strategist",         meta: "synthesis · recommendation",     icon: "sparkle",   colorVar: "--accent"               },
  { id: "judge",      name: "Judge",              meta: "grounding · coherence · retry",  icon: "scale",     colorVar: "--ai-thinking"          },
];

function AgentSelector() {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set(["customer", "analytics", "market", "business", "technical"]));

  const filtered = SELECTOR_ITEMS.filter((it) =>
    query === "" || it.name.toLowerCase().includes(query.toLowerCase()) || it.meta.toLowerCase().includes(query.toLowerCase())
  );

  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });

  return (
    <div className="p4a-selector" role="listbox" aria-multiselectable="true" aria-label="Select agents">
      <div className="p4a-selector__search">
        <span className="p4a-selector__search-icon"><Icon name="search" size="xs" /></span>
        <input
          className="p4a-selector__input"
          type="search"
          placeholder="Filter agents…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Filter agents"
        />
      </div>
      {filtered.length === 0
        ? <p className="p4a-selector__empty">No agents match "{query}"</p>
        : (
          <ul className="p4a-selector__list" role="group">
            {filtered.map((item) => (
              <li
                key={item.id}
                className="p4a-selector__item"
                role="option"
                aria-selected={selected.has(item.id)}
                tabIndex={0}
                style={vars({ "--p4a-agent-color": `var(${item.colorVar})` })}
                onClick={() => toggle(item.id)}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(item.id); } }}
              >
                <span className="p4a-selector__item-icon">
                  <Icon name={item.icon} size="xs" />
                </span>
                <span className="p4a-selector__item-text">
                  <span className="p4a-selector__item-name">{item.name}</span>
                  <span className="p4a-selector__item-meta">{item.meta}</span>
                </span>
                {selected.has(item.id) && (
                  <span className="p4a-selector__item-check" aria-hidden="true">
                    <Icon name="check" size="xs" />
                  </span>
                )}
              </li>
            ))}
          </ul>
        )
      }
    </div>
  );
}

/* ═══════════════════════════════════════════════════════ 6. TIMELINE ═══ */

type Stage = { name: string; status: AgentStatus; time: string; dur: string; note: string };

const PIPELINE_STAGES: Stage[] = [
  { name: "Evidence",       status: "done",     time: "14:22:01", dur: "4.2 s",  note: "5 sources · 1,204 records · scenario sample" },
  { name: "Analyst team",   status: "done",     time: "14:22:05", dur: "38.6 s", note: "5 analysts in parallel · customer led" },
  { name: "Recall",         status: "done",     time: "14:22:05", dur: "1.1 s",  note: "3 relevant lessons retrieved" },
  { name: "Debate",         status: "done",     time: "14:22:44", dur: "22.1 s", note: "2 rounds · advocate vs skeptic" },
  { name: "Strategist",     status: "done",     time: "14:23:06", dur: "11.8 s", note: "recommendation drafted + lesson injection" },
  { name: "Judge",          status: "degraded", time: "14:23:18", dur: "6.4 s",  note: "1 revision triggered · grounding 0.71" },
  { name: "Risk",           status: "running",  time: "14:23:24", dur: "—",      note: "evaluating 5 dimensions" },
  { name: "Governance",     status: "waiting",  time: "—",        dur: "—",      note: "awaiting risk evaluation" },
  { name: "Human approval", status: "waiting",  time: "—",        dur: "—",      note: "HITL enabled — will pause here" },
];

function AgentTimeline({ stages }: { stages: Stage[] }) {
  return (
    <ol className="p4a-timeline">
      {stages.map((stage) => {
        const cfg = STATUS_CFG[stage.status];
        const style = vars({ "--p4a-tl-fill": `var(${cfg.fill})` });
        return (
          <li key={stage.name} className="p4a-tl-row" style={style} data-live={cfg.live ? "true" : undefined}>
            <span className="p4a-tl-marker" aria-label={`${stage.name}: ${cfg.label}`}>
              {cfg.live
                ? <span className="p4a-node-pulse" style={{ width: "var(--space-8)", height: "var(--space-8)", borderRadius: "var(--radius-pill)", display: "block" }} />
                : <Icon name={cfg.icon} size="xs" />
              }
            </span>
            <div className="p4a-tl-body">
              <div className="p4a-tl-head">
                <span className="p4a-tl-node">{stage.name}</span>
                <StatusBadge status={stage.status} />
              </div>
              <p className="p4a-tl-note">{stage.note}</p>
            </div>
            <div className="p4a-tl-meta">
              <span className="p4a-tl-time">{stage.time}</span>
              <span className="p4a-tl-dur">{stage.dur}</span>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

/* ═══════════════════════════════════════════════════════ 7. QUEUE ═══ */

type QueueItem = { id: string; title: string; model: string; priority: Priority; status: AgentStatus; queued: string; current?: boolean };

const PRIORITY_COLORS: Record<Priority, string> = {
  high:   "--ai-failed",
  medium: "--ai-degraded",
  low:    "--ai-waiting",
};

const QUEUE_ITEMS: QueueItem[] = [
  { id: "q-001", title: "Adopt usage-based pricing tier",         model: "claude-sonnet-4-6", priority: "high",   status: "running",  queued: "14:21:04", current: true },
  { id: "q-002", title: "Sunset legacy mobile SDK v2",            model: "claude-sonnet-4-6", priority: "high",   status: "waiting",  queued: "14:20:50" },
  { id: "q-003", title: "Prioritize SSO for enterprise tier",     model: "claude-sonnet-4-6", priority: "medium", status: "waiting",  queued: "14:18:12" },
  { id: "q-004", title: "Launch AI changelog digest feature",     model: "claude-sonnet-4-6", priority: "medium", status: "waiting",  queued: "14:10:55" },
  { id: "q-005", title: "Expand to EU data residency",            model: "claude-sonnet-4-6", priority: "low",    status: "waiting",  queued: "14:05:30" },
];

function AgentQueue({ items }: { items: QueueItem[] }) {
  return (
    <div className="p4a-queue" role="list" aria-label="Evaluation queue">
      <div className="p4a-queue__head" aria-hidden="true">
        <span>Queue · {items.length} pending</span>
        <span>Queued at</span>
      </div>
      {items.map((item, i) => (
        <div
          key={item.id}
          className="p4a-queue-item"
          role="listitem"
          aria-current={item.current ? "true" : undefined}
          tabIndex={0}
          style={vars({ "--p4a-priority-color": `var(${PRIORITY_COLORS[item.priority]})` })}
        >
          <span className="p4a-queue-item__rank">{i + 1}</span>
          <span className="p4a-queue-item__priority" title={`Priority: ${item.priority}`} aria-label={`${item.priority} priority`} />
          <span className="p4a-queue-item__text">
            <span className="p4a-queue-item__title">{item.title}</span>
            <span className="p4a-queue-item__sub">{item.model}</span>
          </span>
          <span className="p4a-queue-item__meta">
            <StatusBadge status={item.status} />
            <span className="p4a-queue-item__time">{item.queued}</span>
          </span>
        </div>
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════ 8. DEPENDENCY GRAPH ═══ */

// Pipeline nodes with their positions in the SVG viewBox (560×230).
// Layout: Evidence → [5 analysts || Recall] → Debate → Strategist → Judge → Risk → Governance.
type NodeDef = { id: string; label: string; cx: number; cy: number; r: number; status: AgentStatus; analyst?: boolean };

const GRAPH_NODES: NodeDef[] = [
  { id: "evidence",    label: "Evidence",    cx: 36,  cy: 115, r: 12, status: "done" },
  { id: "customer",    label: "Customer",    cx: 136, cy: 20,  r: 10, status: "done",    analyst: true },
  { id: "analytics",   label: "Analytics",  cx: 136, cy: 55,  r: 10, status: "done",    analyst: true },
  { id: "market",      label: "Market",     cx: 136, cy: 90,  r: 10, status: "done",    analyst: true },
  { id: "business",    label: "Business",   cx: 136, cy: 125, r: 10, status: "done",    analyst: true },
  { id: "technical",   label: "Technical",  cx: 136, cy: 160, r: 10, status: "done",    analyst: true },
  { id: "recall",      label: "Recall",     cx: 136, cy: 200, r: 10, status: "done" },
  { id: "debate",      label: "Debate",     cx: 250, cy: 70,  r: 12, status: "done" },
  { id: "strategist",  label: "Strategist", cx: 360, cy: 115, r: 12, status: "done" },
  { id: "judge",       label: "Judge",      cx: 445, cy: 115, r: 12, status: "degraded" },
  { id: "risk",        label: "Risk",       cx: 500, cy: 115, r: 12, status: "running" },
  { id: "governance",  label: "Governance", cx: 548, cy: 115, r: 10, status: "waiting" },
];

// Edges: [from_id, to_id, type]
type EdgeType = "normal" | "active" | "recall";
type EdgeDef = [string, string, EdgeType];

const GRAPH_EDGES: EdgeDef[] = [
  // Evidence → analysts
  ["evidence", "customer",   "normal"],
  ["evidence", "analytics",  "normal"],
  ["evidence", "market",     "normal"],
  ["evidence", "business",   "normal"],
  ["evidence", "technical",  "normal"],
  // Evidence → recall
  ["evidence", "recall",     "recall"],
  // Analysts → debate
  ["customer",  "debate",    "normal"],
  ["analytics", "debate",    "normal"],
  ["market",    "debate",    "normal"],
  ["business",  "debate",    "normal"],
  ["technical", "debate",    "normal"],
  // Recall → strategist (memory injection)
  ["recall",    "strategist","recall"],
  // Main spine
  ["debate",    "strategist","normal"],
  ["strategist","judge",     "normal"],
  // Judge → risk (active edge because risk is running)
  ["judge",     "risk",      "active"],
  ["risk",      "governance","active"],
];

function getNode(id: string): NodeDef {
  return GRAPH_NODES.find((n) => n.id === id)!;
}

function nodeStatusClass(status: AgentStatus): string {
  if (status === "running")  return "p4a-node--active";
  if (status === "done")     return "p4a-node--done";
  if (status === "degraded") return "p4a-node--degraded";
  if (status === "failed")   return "p4a-node--failed";
  return "";
}

function DependencyGraph() {
  const [focusId, setFocusId] = useState<string | null>(null);

  return (
    <div className="p4a-dep-graph">
      <svg
        className="p4a-dep-graph__svg"
        viewBox="0 0 570 230"
        role="img"
        aria-label="ProductAgents pipeline dependency graph"
      >
        <defs>
          <marker id="p4a-arrow" viewBox="0 0 6 6" refX="6" refY="3" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M0,0 L6,3 L0,6 z" fill="var(--ai-edge)" />
          </marker>
          <marker id="p4a-arrow-active" viewBox="0 0 6 6" refX="6" refY="3" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M0,0 L6,3 L0,6 z" fill="var(--ai-edge-active)" />
          </marker>
          <marker id="p4a-arrow-recall" viewBox="0 0 6 6" refX="6" refY="3" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M0,0 L6,3 L0,6 z" fill="var(--ai-thinking)" opacity="0.7" />
          </marker>
        </defs>

        {/* Edges drawn first so nodes sit on top */}
        {GRAPH_EDGES.map(([fromId, toId, type]) => {
          const from = getNode(fromId);
          const to = getNode(toId);
          // Simple straight line, shortened at both ends by node radius + 3px gap
          const dx = to.cx - from.cx;
          const dy = to.cy - from.cy;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const startGap = from.r + 3;
          const endGap = to.r + 8; // extra for arrowhead
          const x1 = from.cx + (dx / dist) * startGap;
          const y1 = from.cy + (dy / dist) * startGap;
          const x2 = to.cx - (dx / dist) * endGap;
          const y2 = to.cy - (dy / dist) * endGap;
          const markerEnd = type === "active" ? "url(#p4a-arrow-active)"
            : type === "recall" ? "url(#p4a-arrow-recall)" : "url(#p4a-arrow)";
          return (
            <line
              key={`${fromId}-${toId}`}
              x1={x1} y1={y1} x2={x2} y2={y2}
              className={`p4a-edge${type === "active" ? " p4a-edge--active" : type === "recall" ? " p4a-edge--recall" : ""}`}
              markerEnd={markerEnd}
            />
          );
        })}

        {/* Nodes */}
        {GRAPH_NODES.map((node) => {
          const cfg = STATUS_CFG[node.status];
          const isFocused = focusId === node.id;
          return (
            <g
              key={node.id}
              className={`p4a-node ${nodeStatusClass(node.status)}`}
              role="button"
              aria-label={`${node.label}: ${cfg.label}`}
              aria-pressed={isFocused}
              tabIndex={0}
              onFocus={() => setFocusId(node.id)}
              onBlur={() => setFocusId(null)}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setFocusId(node.id); }}
            >
              <circle
                className="p4a-node-circle"
                cx={node.cx}
                cy={node.cy}
                r={node.r}
              />
              {/* Pulsing dot for running node */}
              {node.status === "running" && (
                <circle className="p4a-node-pulse" cx={node.cx} cy={node.cy} r={4} />
              )}
              {/* Node label — below the node */}
              <text
                className="p4a-node-label"
                x={node.cx}
                y={node.cy + node.r + 11}
                aria-hidden="true"
              >
                {node.label}
              </text>
              {/* Focus ring drawn as a larger circle */}
              {isFocused && (
                <circle
                  cx={node.cx}
                  cy={node.cy}
                  r={node.r + 3}
                  fill="none"
                  stroke="var(--border-focus)"
                  strokeWidth="2"
                  aria-hidden="true"
                />
              )}
            </g>
          );
        })}
      </svg>
      <div className="p4a-graph-legend">
        <span className="p4a-graph-legend__item">
          <span className="p4a-graph-legend__dot" style={{ background: "var(--ai-done)" }} />
          Done
        </span>
        <span className="p4a-graph-legend__item">
          <span className="p4a-graph-legend__dot" style={{ background: "var(--ai-running)" }} />
          Running
        </span>
        <span className="p4a-graph-legend__item">
          <span className="p4a-graph-legend__dot" style={{ background: "var(--ai-degraded)" }} />
          Degraded
        </span>
        <span className="p4a-graph-legend__item">
          <span className="p4a-graph-legend__dot" style={{ background: "var(--ai-waiting)" }} />
          Waiting
        </span>
        <span className="p4a-graph-legend__item">
          <span className="p4a-graph-legend__dot" style={{ background: "var(--ai-thinking)", opacity: 0.7 }} />
          Recall path
        </span>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════ GALLERY ═══ */

export function Phase4Agents() {
  const [selectedAgent, setSelectedAgent] = useState<string>("customer");
  const profileAgent = AGENTS.find((a) => a.id === selectedAgent) ?? AGENTS[0];

  return (
    <>
      <div className="sg-subband">
        <h3>4A · Agent Components</h3>
        <span>
          The UI vocabulary for AI agent state — status badges, agent cards, profile, capabilities,
          selector, pipeline timeline, evaluation queue, and dependency graph. Every status pairs
          colour with a glyph + label; the running state is further distinguished by animation.
        </span>
      </div>

      {/* 1. STATUS BADGE ─────────────────────────────────────────────────── */}
      <Section
        id="p4a-status-badge"
        title="Status badge"
        desc="Colour+glyph+label pill for every agent lifecycle state. Running uses an animated dot (amber = live); all others use a static glyph. Colour is never the only channel."
      >
        <div className="sg-card p4a-stack">
          <Specimen label="all states">
            <div className="p4a-row">
              {(Object.keys(STATUS_CFG) as AgentStatus[]).map((s) => (
                <StatusBadge key={s} status={s} />
              ))}
            </div>
          </Specimen>
          <Specimen label="inline with text">
            <span style={{ font: "var(--text-body-s)", color: "var(--text-secondary)" }}>
              The Risk node is <StatusBadge status="running" /> and Governance is <StatusBadge status="waiting" />.
            </span>
          </Specimen>
        </div>
      </Section>

      {/* 2. AGENT CARD ───────────────────────────────────────────────────── */}
      <Section
        id="p4a-agent-card"
        title="Agent card"
        desc="Compact card for one agent in a grid: avatar icon, name, role, status badge, and confidence gauge. Click to select; keyboard-operable with Enter / Space."
      >
        <div className="sg-card">
          <div className="p4a-agents-grid" role="listbox" aria-label="Agents" aria-multiselectable="false">
            {AGENTS.map((agent) => (
              <AgentCard
                key={agent.id}
                agent={agent}
                selected={selectedAgent === agent.id}
                onSelect={() => setSelectedAgent(agent.id)}
              />
            ))}
          </div>
        </div>
      </Section>

      {/* 3. PROFILE ─────────────────────────────────────────────────────── */}
      <Section
        id="p4a-profile"
        title="Agent profile"
        desc="Full profile panel for a selected agent: large avatar, name, role path, description, and key run metrics. Select an agent card above to change the profile."
      >
        <div className="sg-card">
          <AgentProfile agent={profileAgent} />
        </div>
      </Section>

      {/* 4. CAPABILITY LIST ──────────────────────────────────────────────── */}
      <Section
        id="p4a-cap-list"
        title="Capability list"
        desc="What tools and knowledge sources an agent can access. Each entry: category icon, name, one-line description, and a tinted tag. Colour is reinforced by position and icon."
      >
        <div className="sg-card">
          <CapabilityList items={CAPABILITIES} />
        </div>
      </Section>

      {/* 5. SELECTOR ─────────────────────────────────────────────────────── */}
      <Section
        id="p4a-selector"
        title="Agent selector"
        desc="Multi-select listbox for choosing which agents run. Filter by name or keyword; toggle items with click or Enter / Space. Shows a checkmark on selected items."
      >
        <div className="sg-card p4a-grid-2">
          <AgentSelector />
          <div style={{ font: "var(--text-body-s)", color: "var(--text-secondary)", display: "grid", gap: "var(--space-8)", alignContent: "start" }}>
            <p style={{ margin: 0, fontWeight: "var(--fw-semibold)", color: "var(--text-primary)" }}>Usage</p>
            <p style={{ margin: 0 }}>Toggle any analyst off to exclude it from the next run. The Strategist and Judge are always enabled — they synthesise whatever analysts provide.</p>
            <p style={{ margin: 0 }}>The filter is case-insensitive and matches name or meta tags (e.g. "metrics" finds Analytics).</p>
          </div>
        </div>
      </Section>

      {/* 6. TIMELINE ─────────────────────────────────────────────────────── */}
      <Section
        id="p4a-timeline"
        title="Pipeline timeline"
        desc="Vertical execution timeline for one evaluation run: each stage has a status marker on a rail, timing, duration, and a note. Amber = live; teal = settled."
      >
        <div className="sg-card">
          <AgentTimeline stages={PIPELINE_STAGES} />
        </div>
      </Section>

      {/* 7. QUEUE ────────────────────────────────────────────────────────── */}
      <Section
        id="p4a-queue"
        title="Evaluation queue"
        desc="Ordered list of pending evaluation runs with priority colour, initiative name, model, and status. The current (running) item is highlighted amber. Keyboard-focusable rows."
      >
        <div className="sg-card">
          <AgentQueue items={QUEUE_ITEMS} />
        </div>
      </Section>

      {/* 8. DEPENDENCY GRAPH ─────────────────────────────────────────────── */}
      <Section
        id="p4a-dep-graph"
        title="Dependency graph"
        desc="SVG pipeline graph: Evidence fans out to 5 parallel analysts and Recall, which converge into Debate and Strategist, then Judge → Risk → Governance. Active edges animate. Tab between nodes."
      >
        <div className="sg-card">
          <DependencyGraph />
        </div>
      </Section>
    </>
  );
}
