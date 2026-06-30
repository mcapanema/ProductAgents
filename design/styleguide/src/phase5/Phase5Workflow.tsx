import { useState } from "react";
import type { CSSProperties } from "react";
import { Section, Specimen } from "../sg";
import "./phase5a-workflow.css";

const vars = (o: Record<string, string>): CSSProperties => o as CSSProperties;

/* ── Icons ──────────────────────────────────────────────────────────────────── */

type IconName =
  | "circle-dot"
  | "check-circle"
  | "x-circle"
  | "clock"
  | "flag"
  | "link"
  | "share"
  | "list"
  | "chevron-right"
  | "refresh"
  | "alert";

const PATHS: Record<IconName, React.ReactNode> = {
  "circle-dot": <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="2.5" fill="currentColor" stroke="none" /></>,
  "check-circle": <><circle cx="12" cy="12" r="8" /><path d="M8.5 12.5l2.3 2.3L16 9.5" /></>,
  "x-circle": <><circle cx="12" cy="12" r="8" /><path d="M9 9l6 6M15 9l-6 6" /></>,
  clock: <><circle cx="12" cy="12" r="8" /><path d="M12 7.5v5l3.2 1.8" /></>,
  flag: <><path d="M6 21V4" /><path d="M6 4h11l-2.5 3.5L17 11H6" /></>,
  link: <><path d="M9.5 14.5l5-5" /><path d="M8 16a3.5 3.5 0 010-5l1.5-1.5" /><path d="M16 8a3.5 3.5 0 010 5l-1.5 1.5" /></>,
  share: <><circle cx="6" cy="12" r="2.5" /><circle cx="17" cy="6" r="2.5" /><circle cx="17" cy="18" r="2.5" /><path d="M8.2 10.8L14.8 7.2M8.2 13.2l6.6 3.6" /></>,
  list: <><path d="M9 6h11M9 12h11M9 18h11" /><circle cx="4.5" cy="6" r="1.2" fill="currentColor" stroke="none" /><circle cx="4.5" cy="12" r="1.2" fill="currentColor" stroke="none" /><circle cx="4.5" cy="18" r="1.2" fill="currentColor" stroke="none" /></>,
  "chevron-right": <path d="M9 6l6 6-6 6" />,
  refresh: <><path d="M4 12a8 8 0 0114-5.3L20 9" /><path d="M20 4v5h-5" /><path d="M20 12a8 8 0 01-14 5.3L4 15" /><path d="M4 20v-5h5" /></>,
  alert: <><path d="M12 4l9 16H3z" /><path d="M12 10v4" /><path d="M12 17h.01" /></>,
};

function Icon({ name, size = "sm" }: { name: IconName; size?: "xs" | "sm" | "md" }) {
  return (
    <svg
      className={`p5a-ico p5a-ico--${size}`}
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

/* ── Shared status vocab (reuses semantic tokens, no new colors) ─────────────── */

type InitiativeStatus = "proposed" | "planned" | "in_progress" | "shipped" | "cancelled";
type FeatureStatus = "idea" | "planned" | "in_progress" | "shipped" | "deprecated";
type Priority = "low" | "medium" | "high" | "critical";

const INITIATIVE_STATUS_CFG: Record<InitiativeStatus, { label: string; icon: IconName; color: string; text: string }> = {
  proposed:    { label: "Proposed",    icon: "circle-dot",   color: "var(--text-tertiary)", text: "var(--text-tertiary)" },
  planned:     { label: "Planned",     icon: "clock",        color: "var(--info)",          text: "var(--text-info)" },
  in_progress: { label: "In progress", icon: "circle-dot",   color: "var(--accent)",        text: "var(--accent-text)" },
  shipped:     { label: "Shipped",     icon: "check-circle", color: "var(--success)",       text: "var(--text-success)" },
  cancelled:   { label: "Cancelled",   icon: "x-circle",     color: "var(--text-disabled)", text: "var(--text-disabled)" },
};

const FEATURE_STATUS_CFG: Record<FeatureStatus, { label: string; icon: IconName; color: string; text: string }> = {
  idea:        { label: "Idea",        icon: "circle-dot",   color: "var(--text-tertiary)", text: "var(--text-tertiary)" },
  planned:     { label: "Planned",     icon: "clock",        color: "var(--info)",          text: "var(--text-info)" },
  in_progress: { label: "In progress", icon: "circle-dot",   color: "var(--accent)",        text: "var(--accent-text)" },
  shipped:     { label: "Shipped",     icon: "check-circle", color: "var(--success)",       text: "var(--text-success)" },
  deprecated:  { label: "Deprecated",  icon: "x-circle",     color: "var(--text-disabled)", text: "var(--text-disabled)" },
};

const PRIORITY_CFG: Record<Priority, { label: string; color: string }> = {
  low:      { label: "Low",      color: "var(--text-tertiary)" },
  medium:   { label: "Medium",   color: "var(--info)" },
  high:     { label: "High",     color: "var(--warning)" },
  critical: { label: "Critical", color: "var(--danger)" },
};

/* ── 1. Task Status ────────────────────────────────────────────────────────── */

function TaskStatusBadge({ status, kind }: { status: InitiativeStatus | FeatureStatus; kind: "initiative" | "feature" }) {
  const cfg = kind === "initiative" ? INITIATIVE_STATUS_CFG[status as InitiativeStatus] : FEATURE_STATUS_CFG[status as FeatureStatus];
  return (
    <span
      className="p5a-status-badge"
      style={vars({ "--p5a-badge-color": cfg.color, "--p5a-badge-text": cfg.text })}
    >
      <Icon name={cfg.icon} size="xs" />
      {cfg.label}
    </span>
  );
}

function PriorityBadge({ priority }: { priority: Priority }) {
  const cfg = PRIORITY_CFG[priority];
  return (
    <span className="p5a-priority-badge" style={vars({ "--p5a-priority-color": cfg.color })}>
      <Icon name="flag" size="xs" />
      {cfg.label}
    </span>
  );
}

/* ── 2. Stage Header ───────────────────────────────────────────────────────── */

function StageHeader({
  title,
  count,
  status,
  action,
}: {
  title: string;
  count?: number;
  status?: InitiativeStatus;
  action?: string;
}) {
  return (
    <div className="p5a-stage-header">
      <div className="p5a-stage-header__title-row">
        <h4 className="p5a-stage-header__title">{title}</h4>
        {typeof count === "number" && <span className="p5a-stage-header__count">{count}</span>}
      </div>
      <div className="p5a-stage-header__meta">
        {status && <TaskStatusBadge status={status} kind="initiative" />}
        {action && <button type="button" className="p5a-stage-header__action">{action}</button>}
      </div>
    </div>
  );
}

/* ── 3. Task Card ──────────────────────────────────────────────────────────── */

interface TaskCardData {
  title: string;
  description: string;
  status: InitiativeStatus;
  priority: Priority;
  owner: string;
  quarter: string;
}

function TaskCard({ data }: { data: TaskCardData }) {
  return (
    <article className="p5a-task-card">
      <header className="p5a-task-card__head">
        <h5 className="p5a-task-card__title">{data.title}</h5>
        <TaskStatusBadge status={data.status} kind="initiative" />
      </header>
      <p className="p5a-task-card__desc">{data.description}</p>
      <footer className="p5a-task-card__foot">
        <PriorityBadge priority={data.priority} />
        <span className="p5a-task-card__owner">{data.owner}</span>
        <span className="p5a-task-card__quarter">{data.quarter}</span>
      </footer>
    </article>
  );
}

const TASK_CARDS: TaskCardData[] = [
  { title: "Usage-based billing", description: "Move mid-market accounts off flat-rate plans onto metered usage.", status: "in_progress", priority: "critical", owner: "R. Castellan", quarter: "Q3 2026" },
  { title: "Mobile offline mode", description: "Cache the last session locally so the app stays usable without a connection.", status: "planned", priority: "medium", owner: "M. Owusu", quarter: "Q4 2026" },
  { title: "Legacy export format", description: "Deprecate the CSV exporter once the new reporting API ships.", status: "cancelled", priority: "low", owner: "T. Iyer", quarter: "Q2 2026" },
];

/* ── 4. Milestone ──────────────────────────────────────────────────────────── */

interface MilestoneData {
  label: string;
  date: string;
  state: "reached" | "upcoming" | "at-risk";
}

const MILESTONE_CFG: Record<MilestoneData["state"], { icon: IconName; color: string }> = {
  reached:  { icon: "check-circle", color: "var(--success)" },
  upcoming: { icon: "flag",         color: "var(--text-tertiary)" },
  "at-risk": { icon: "alert",       color: "var(--danger)" },
};

function Milestone({ data }: { data: MilestoneData }) {
  const cfg = MILESTONE_CFG[data.state];
  return (
    <li className="p5a-milestone" data-state={data.state}>
      <span className="p5a-milestone__marker" style={vars({ "--p5a-ms-color": cfg.color })}>
        <Icon name={cfg.icon} size="xs" />
      </span>
      <span className="p5a-milestone__label">{data.label}</span>
      <span className="p5a-milestone__date">{data.date}</span>
    </li>
  );
}

const MILESTONES: MilestoneData[] = [
  { label: "Beta cohort onboarded", date: "Apr 14", state: "reached" },
  { label: "30-day retention checkpoint", date: "May 14", state: "reached" },
  { label: "60-day revenue checkpoint", date: "Jun 13", state: "at-risk" },
  { label: "GA rollout", date: "Jul 1", state: "upcoming" },
];

/* ── 5. Progress Timeline (roadmap, by quarter) ───────────────────────────────── */

interface RoadmapQuarter {
  quarter: string;
  state: "done" | "current" | "future";
  items: string[];
}

const ROADMAP: RoadmapQuarter[] = [
  { quarter: "Q1 2026", state: "done", items: ["Connector framework", "GitHub sync"] },
  { quarter: "Q2 2026", state: "done", items: ["Org memory store", "Jira sync"] },
  { quarter: "Q3 2026", state: "current", items: ["Usage-based billing", "Risk layer"] },
  { quarter: "Q4 2026", state: "future", items: ["Mobile offline mode"] },
];

function ProgressTimeline() {
  return (
    <ol className="p5a-progress-timeline">
      {ROADMAP.map((q) => (
        <li key={q.quarter} className="p5a-progress-timeline__step" data-state={q.state}>
          <span className="p5a-progress-timeline__dot" aria-hidden="true" />
          <div className="p5a-progress-timeline__body">
            <span className="p5a-progress-timeline__quarter">{q.quarter}</span>
            <ul className="p5a-progress-timeline__items">
              {q.items.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </div>
        </li>
      ))}
    </ol>
  );
}

/* ── 6. Pipeline View (bird's-eye chip row of a workflow definition) ─────────── */

const PIPELINE_STAGES = [
  "Evidence", "Analysts ×5", "Recall", "Debate", "Strategist", "Judge", "Risk", "Governance", "Approval",
];

function PipelineView() {
  return (
    <div className="p5a-pipeline-view" role="list" aria-label="evaluate_initiative workflow stages">
      {PIPELINE_STAGES.map((stage, i) => (
        <span key={stage} className="p5a-pipeline-view__chip" role="listitem">
          {stage}
          {i < PIPELINE_STAGES.length - 1 && <Icon name="chevron-right" size="xs" />}
        </span>
      ))}
    </div>
  );
}

/* ── 7. Workflow Graph / Node / Edge (workflow definition, not a live run) ───── */

interface WfNode { id: string; label: string; cx: number; cy: number; }
interface WfEdge { from: string; to: string }

const WF_NODES: WfNode[] = [
  { id: "evidence", label: "Evidence", cx: 60, cy: 90 },
  { id: "analysts", label: "Analysts (×5)", cx: 200, cy: 40 },
  { id: "recall", label: "Recall", cx: 200, cy: 140 },
  { id: "debate", label: "Debate", cx: 340, cy: 90 },
  { id: "strategist", label: "Strategist", cx: 470, cy: 90 },
  { id: "judge", label: "Judge", cx: 590, cy: 90 },
];

const WF_EDGES: WfEdge[] = [
  { from: "evidence", to: "analysts" },
  { from: "evidence", to: "recall" },
  { from: "analysts", to: "debate" },
  { from: "recall", to: "debate" },
  { from: "debate", to: "strategist" },
  { from: "strategist", to: "judge" },
];

function WorkflowGraph() {
  const byId = Object.fromEntries(WF_NODES.map((n) => [n.id, n]));
  return (
    <svg className="p5a-wf-graph" viewBox="0 0 650 190" role="img" aria-label="evaluate_initiative workflow definition graph">
      <defs>
        <marker id="p5a-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M0 0L8 4L0 8z" className="p5a-wf-edge-arrow" />
        </marker>
      </defs>
      {WF_EDGES.map((e) => {
        const a = byId[e.from];
        const b = byId[e.to];
        return (
          <line
            key={`${e.from}-${e.to}`}
            x1={a.cx + 26} y1={a.cy} x2={b.cx - 28} y2={b.cy}
            className="p5a-wf-edge"
            markerEnd="url(#p5a-arrow)"
          />
        );
      })}
      {WF_NODES.map((n) => (
        <g key={n.id} className="p5a-wf-node" role="img" aria-label={n.label}>
          <rect className="p5a-wf-node__rect" x={n.cx - 26} y={n.cy - 16} width={52} height={32} rx={8} />
          <text className="p5a-wf-node__label" x={n.cx} y={n.cy + 32} textAnchor="middle" aria-hidden="true">{n.label}</text>
        </g>
      ))}
    </svg>
  );
}

/* ── 8. Dependency Graph (cross-initiative dependencies) ──────────────────────── */

interface DepLink { blocker: string; blocked: string }

const DEP_INITIATIVES = ["Usage-based billing", "Metering pipeline", "Invoice redesign", "Mobile offline mode"];
const DEP_LINKS: DepLink[] = [
  { blocker: "Metering pipeline", blocked: "Usage-based billing" },
  { blocker: "Usage-based billing", blocked: "Invoice redesign" },
];

function DependencyGraph() {
  return (
    <ul className="p5a-dep-graph" aria-label="initiative dependencies">
      {DEP_INITIATIVES.map((name) => {
        const blockedBy = DEP_LINKS.filter((l) => l.blocked === name).map((l) => l.blocker);
        return (
          <li key={name} className="p5a-dep-graph__row">
            <span className="p5a-dep-graph__node">{name}</span>
            {blockedBy.length > 0 && (
              <span className="p5a-dep-graph__deps">
                <Icon name="link" size="xs" />
                blocked by {blockedBy.join(", ")}
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
}

/* ── 9. Execution Queue (connector sync jobs) ─────────────────────────────────── */

interface SyncJob {
  connector: string;
  status: "queued" | "syncing" | "done" | "error";
  cursor: string;
  time: string;
}

const SYNC_JOBS: SyncJob[] = [
  { connector: "github · acme/web", status: "syncing", cursor: "issue #4821", time: "running 12s" },
  { connector: "jira · PROD", status: "queued", cursor: "—", time: "waiting" },
  { connector: "github · acme/mobile", status: "done", cursor: "issue #312", time: "14:22:01" },
  { connector: "jira · GROWTH", status: "error", cursor: "GROWTH-88", time: "14:18:40" },
];

const SYNC_STATUS_CFG: Record<SyncJob["status"], { icon: IconName; color: string }> = {
  queued: { icon: "clock", color: "var(--text-tertiary)" },
  syncing: { icon: "refresh", color: "var(--accent)" },
  done: { icon: "check-circle", color: "var(--success)" },
  error: { icon: "x-circle", color: "var(--danger)" },
};

function ExecutionQueue() {
  return (
    <div className="p5a-queue">
      <div className="p5a-queue__head">
        <Icon name="list" size="xs" />
        Connector sync queue
      </div>
      <ol className="p5a-queue__list">
        {SYNC_JOBS.map((job, i) => {
          const cfg = SYNC_STATUS_CFG[job.status];
          return (
            <li key={job.connector} className="p5a-queue-item" style={vars({ "--p5a-queue-color": cfg.color })}>
              <span className="p5a-queue-item__rank">{i + 1}</span>
              <Icon name={cfg.icon} size="xs" />
              <span className="p5a-queue-item__name">{job.connector}</span>
              <span className="p5a-queue-item__cursor">{job.cursor}</span>
              <span className="p5a-queue-item__time">{job.time}</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

/* ── Gallery ───────────────────────────────────────────────────────────────── */

export function Phase5Workflow() {
  const [density, setDensity] = useState<"comfortable" | "compact">("comfortable");

  return (
    <div data-density={density}>
      <div className="sg-intro">
        <h2>Workflow components</h2>
        <p>
          Phase 5A — planning and orchestration primitives: roadmap, initiative
          dependencies, and job queues. Distinct from Phase 4's live AI-run
          surface; this layer is the product-planning view (Initiative, Feature,
          RoadmapItem), reusing the same status/priority semantic tokens.
        </p>
        <label className="sg-density-toggle">
          <input
            type="checkbox"
            checked={density === "compact"}
            onChange={(e) => setDensity(e.target.checked ? "compact" : "comfortable")}
          />
          Compact density
        </label>
      </div>

      <Section id="p5a-task-status" title="Task Status" desc="Initiative/Feature status and priority badges, reusing existing semantic color tokens.">
        <Specimen label="initiative status">
          <div className="p5a-row">
            {(Object.keys(INITIATIVE_STATUS_CFG) as InitiativeStatus[]).map((s) => (
              <TaskStatusBadge key={s} status={s} kind="initiative" />
            ))}
          </div>
        </Specimen>
        <Specimen label="priority">
          <div className="p5a-row">
            {(Object.keys(PRIORITY_CFG) as Priority[]).map((p) => (
              <PriorityBadge key={p} priority={p} />
            ))}
          </div>
        </Specimen>
      </Section>

      <Section id="p5a-stage-header" title="Stage Header" desc="Reusable section header for a named stage or group: title, count, status, optional action.">
        <Specimen label="default">
          <StageHeader title="In progress" count={4} status="in_progress" action="View all" />
        </Specimen>
        <Specimen label="no action">
          <StageHeader title="Shipped this quarter" count={9} status="shipped" />
        </Specimen>
      </Section>

      <Section id="p5a-task-card" title="Task Card" desc="Generic Initiative/Feature summary card.">
        <Specimen label="grid">
          <div className="p5a-task-grid">
            {TASK_CARDS.map((t) => <TaskCard key={t.title} data={t} />)}
          </div>
        </Specimen>
      </Section>

      <Section id="p5a-milestone" title="Milestone" desc="Roadmap checkpoint marker — reached, upcoming, or at-risk.">
        <Specimen label="default">
          <ul className="p5a-milestone-list">
            {MILESTONES.map((m) => <Milestone key={m.label} data={m} />)}
          </ul>
        </Specimen>
      </Section>

      <Section id="p5a-progress-timeline" title="Progress Timeline" desc="Compact vertical stepper for roadmap quarters.">
        <Specimen label="default">
          <ProgressTimeline />
        </Specimen>
      </Section>

      <Section id="p5a-pipeline-view" title="Pipeline View" desc="Bird's-eye horizontal chip row of a workflow's stages — a compact alternative to the full graph.">
        <Specimen label="default">
          <PipelineView />
        </Specimen>
      </Section>

      <Section id="p5a-workflow-graph" title="Workflow Graph / Node / Edge" desc="Structural view of a workflow definition (e.g. evaluate_initiative), as registered in WorkflowService — not a live run.">
        <Specimen label="default">
          <WorkflowGraph />
        </Specimen>
      </Section>

      <Section id="p5a-dependency-graph" title="Dependency Graph" desc="Cross-initiative dependencies — which initiatives block which.">
        <Specimen label="default">
          <DependencyGraph />
        </Specimen>
      </Section>

      <Section id="p5a-execution-queue" title="Execution Queue" desc="Ordered queue of pending/running/done jobs — here, connector sync runs.">
        <Specimen label="default">
          <ExecutionQueue />
        </Specimen>
      </Section>
    </div>
  );
}
