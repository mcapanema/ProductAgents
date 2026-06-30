// Phase 4B — Execution & Streaming Reasoning components gallery.
// ExecutionCard, ExecutionTimeline (CENTERPIECE), DebateTurnCard,
// RecommendationCard, JudgmentCard, ApprovalRequestCard, ExecutionProgress,
// ParallelTaskViewer, RetryCard, CancellationBanner, ResumePanelCard,
// LiveLogViewer, StreamingConsole, ToolExecutionCard, ToolCallInspector.
import { useState, useRef } from "react";
import type { CSSProperties, KeyboardEvent as RKE } from "react";
import { Section, Specimen } from "../sg";
import "./phase4b-execution.css";

const vars = (o: Record<string, string>): CSSProperties => o as CSSProperties;

/* ── Types ──────────────────────────────────────────────────────────────────── */

type AgentStatus =
  | "waiting" | "running" | "done" | "degraded"
  | "failed" | "awaiting-human" | "cancelled";

/* ── Icons ──────────────────────────────────────────────────────────────────── */

type IconName =
  | "check" | "circle" | "x" | "warning" | "slash" | "diamond" | "play"
  | "chevron-right" | "chevron-down" | "scale" | "shield" | "sparkle"
  | "refresh" | "chart" | "globe" | "briefcase" | "code"
  | "database" | "plug" | "terminal" | "ban" | "tool";

const PATHS: Record<IconName, React.ReactNode> = {
  check:           <path d="M5 13l4 4L19 7" />,
  circle:          <circle cx="12" cy="12" r="7" fill="none" />,
  x:               <path d="M6 6l12 12M18 6L6 18" />,
  warning:         <><path d="M12 4l9 16H3z" /><path d="M12 10v4" /><path d="M12 17h.01" /></>,
  slash:           <><circle cx="12" cy="12" r="8" /><path d="M7 7l10 10" /></>,
  diamond:         <path d="M12 3l9 9-9 9-9-9z" />,
  play:            <path d="M8 5l11 7-11 7z" />,
  "chevron-right": <path d="M9 6l6 6-6 6" />,
  "chevron-down":  <path d="M6 9l6 6 6-6" />,
  scale:           <><path d="M12 3v18M3 8l9-5 9 5" /><path d="M6 12l-3 6h6z" /><path d="M18 12l-3 6h6z" /></>,
  shield:          <path d="M12 3l8 3.5V12c0 5-8 9-8 9s-8-4-8-9V6.5z" />,
  sparkle:         <path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z" />,
  refresh:         <><path d="M20 7A9 9 0 114 13" /><path d="M20 3v4h-4" /></>,
  chart:           <path d="M3 20h18M6 20V14m4 6V8m4 12V4m4 16v-6" />,
  globe:           <><circle cx="12" cy="12" r="9" /><path d="M2 12h20M12 3a15 15 0 010 18M12 3a15 15 0 000 18" /></>,
  briefcase:       <><rect x="2" y="9" width="20" height="12" rx="2" /><path d="M16 9V7a4 4 0 00-8 0v2" /></>,
  code:            <><path d="M8 9l-3 3 3 3" /><path d="M16 9l3 3-3 3" /><path d="M14 6l-4 12" /></>,
  database:        <><ellipse cx="12" cy="6" rx="7" ry="3" /><path d="M5 6v12c0 1.66 3.13 3 7 3s7-1.34 7-3V6" /><path d="M5 12c0 1.66 3.13 3 7 3s7-1.34 7-3" /></>,
  plug:            <><path d="M9 3v5M15 3v5" /><path d="M6 8h12v3a6 6 0 01-12 0z" /><path d="M12 17v4" /></>,
  terminal:        <><rect x="2" y="3" width="20" height="18" rx="2" /><path d="M7 9l3 3-3 3M13 15h4" /></>,
  ban:             <><circle cx="12" cy="12" r="9" /><path d="M5.6 5.6l12.8 12.8" /></>,
  tool:            <><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3-3a1 1 0 000-1.4l-1.6-1.6a1 1 0 00-1.4 0z" /><path d="M5 20l8.8-8.8m-1.9-1.9L4 20" /></>,
};

function Icon({ name, size = "xs" }: { name: IconName; size?: "xs" | "sm" | "md" }) {
  return (
    <svg
      className={`p4b-ico p4b-ico--${size}`}
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

/* ── Status config ──────────────────────────────────────────────────────────── */

const STATUS_CFG: Record<AgentStatus, {
  label: string; icon: IconName; fill: string; text: string; live?: boolean;
}> = {
  waiting:          { label: "Waiting",        icon: "circle",  fill: "--ai-waiting",        text: "--text-secondary" },
  running:          { label: "Running",        icon: "play",    fill: "--ai-running",        text: "--ai-running-text", live: true },
  done:             { label: "Done",           icon: "check",   fill: "--ai-done",           text: "--ai-done-text" },
  degraded:         { label: "Degraded",       icon: "warning", fill: "--ai-degraded",       text: "--ai-degraded-text" },
  failed:           { label: "Failed",         icon: "x",       fill: "--ai-failed",         text: "--ai-failed-text" },
  "awaiting-human": { label: "Awaiting human", icon: "diamond", fill: "--ai-awaiting-human", text: "--text-link" },
  cancelled:        { label: "Cancelled",      icon: "slash",   fill: "--ai-cancelled",      text: "--text-tertiary" },
};

/* ── Shared sub-components ──────────────────────────────────────────────────── */

function StatusBadge({ status }: { status: AgentStatus }) {
  const cfg = STATUS_CFG[status];
  return (
    <span
      className="p4b-status-badge"
      style={vars({ "--p4b-badge-fill": `var(${cfg.fill})`, "--p4b-badge-text": `var(${cfg.text})` })}
    >
      {cfg.live
        ? <span className="p4b-status-badge__dot" aria-hidden="true" />
        : <span className="p4b-status-badge__icon"><Icon name={cfg.icon} size="xs" /></span>
      }
      {cfg.label}
    </span>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const tier = value < 40 ? "low" : value < 70 ? "medium" : "high";
  return (
    <span
      className="p4b-conf-bar"
      style={vars({ "--p4b-conf-fill": `var(--ai-confidence-${tier})`, "--p4b-conf-pct": `${value}%` })}
    >
      <span className="p4b-conf-bar__track"><span className="p4b-conf-bar__fill" /></span>
      <span className="p4b-conf-bar__val">{value}%</span>
    </span>
  );
}

/* ══════════════════════════════════════════════════════ 1. EXECUTION CARD ═══ */

function ExecutionCard({
  title, status, workflow, startedAt, duration, confidence,
}: {
  title: string; status: AgentStatus; workflow: string; startedAt: string;
  duration?: string; confidence?: number;
}) {
  const cfg = STATUS_CFG[status];
  return (
    <div
      className={`p4b-exec-card p4b-exec-card--${status}`}
      style={vars({ "--p4b-exec-fill": `var(${cfg.fill})` })}
    >
      <div className="p4b-exec-card__bar" aria-hidden="true" />
      <div className="p4b-exec-card__body">
        <div className="p4b-exec-card__head">
          <div>
            <p className="p4b-exec-card__title">{title}</p>
            <p className="p4b-exec-card__wf">{workflow}</p>
          </div>
          <StatusBadge status={status} />
        </div>
        <div className="p4b-exec-card__foot">
          <span className="p4b-exec-card__meta">Started {startedAt}</span>
          {duration && <span className="p4b-exec-card__meta">{duration}</span>}
          {confidence !== undefined && <ConfidenceBar value={confidence} />}
        </div>
      </div>
    </div>
  );
}

/* ════════════════════════════ 2. EXECUTION TIMELINE (CENTERPIECE) ═══════════ */

type TimelineStage = {
  id: string;
  name: string;
  status: AgentStatus;
  time?: string;
  duration?: string;
  detail?: string;
  analystColor?: string; // e.g. "--ai-analyst-customer"
  parallel?: boolean;
};

const MID_RUN_STAGES: TimelineStage[] = [
  { id: "customer",   name: "Customer Research", status: "done",    time: "14:22:01", duration: "38.4 s", detail: "87% confidence. 3 key pain points identified from 1,204 feedback records.",   analystColor: "--ai-analyst-customer",  parallel: true },
  { id: "analytics",  name: "Product Analytics", status: "done",    time: "14:22:01", duration: "41.2 s", detail: "79% confidence. Retention dip in cohorts 30+ days post-onboarding.",          analystColor: "--ai-analyst-analytics", parallel: true },
  { id: "market",     name: "Market",            status: "running", time: "14:22:01",                     detail: "Framing competitive landscape and market timing...",                           analystColor: "--ai-analyst-market",    parallel: true },
  { id: "business",   name: "Business",          status: "waiting",                                                                                                                               analystColor: "--ai-analyst-business",  parallel: true },
  { id: "technical",  name: "Technical",         status: "waiting",                                                                                                                               analystColor: "--ai-analyst-technical", parallel: true },
  { id: "recall",     name: "Recall",            status: "done",    time: "14:22:01", duration: "1.1 s",  detail: "3 relevant lessons retrieved from prior decisions.",                          parallel: true },
  { id: "debate",     name: "Debate",            status: "running",                                       detail: "Round 2 of 2 — Skeptic arguing caution on timeline." },
  { id: "strategist", name: "Strategist",        status: "waiting" },
  { id: "judge",      name: "Judge",             status: "waiting" },
  { id: "risk",       name: "Risk",              status: "waiting" },
  { id: "governance", name: "Governance",        status: "waiting" },
  { id: "approval",   name: "Approval",          status: "waiting" },
];

const APPROVAL_STAGES: TimelineStage[] = [
  { id: "customer",   name: "Customer Research", status: "done",     time: "14:22:01", duration: "38.4 s", detail: "87% confidence. Pain points confirmed across all feedback channels.",       analystColor: "--ai-analyst-customer",  parallel: true },
  { id: "analytics",  name: "Product Analytics", status: "done",     time: "14:22:01", duration: "41.2 s", detail: "79% confidence. Retention metrics support prioritisation.",                 analystColor: "--ai-analyst-analytics", parallel: true },
  { id: "market",     name: "Market",            status: "done",     time: "14:22:01", duration: "35.0 s", detail: "82% confidence. Window open — competitor has not shipped equivalent.",      analystColor: "--ai-analyst-market",    parallel: true },
  { id: "business",   name: "Business",          status: "done",     time: "14:22:01", duration: "29.3 s", detail: "73% confidence. Revenue projection positive; cost within threshold.",       analystColor: "--ai-analyst-business",  parallel: true },
  { id: "technical",  name: "Technical",         status: "degraded", time: "14:22:01", duration: "44.1 s", detail: "Fell back to scenario evidence — connector unavailable. 58% confidence.",  analystColor: "--ai-analyst-technical", parallel: true },
  { id: "recall",     name: "Recall",            status: "done",     time: "14:22:01", duration: "1.1 s",  detail: "3 lessons injected into Strategist context.",                               parallel: true },
  { id: "debate",     name: "Debate",            status: "done",     time: "14:23:00", duration: "22.1 s", detail: "2 rounds complete. Strong market case; technical risk flagged by Skeptic." },
  { id: "strategist", name: "Strategist",        status: "done",     time: "14:23:22", duration: "11.8 s", detail: "Recommendation: phased rollout with milestone checkpoints." },
  { id: "judge",      name: "Judge",             status: "done",     time: "14:23:34", duration: "6.4 s",  detail: "Evidence: 0.84 · Rationale: 0.79 — PASS. 1 revision triggered." },
  { id: "risk",       name: "Risk",              status: "done",     time: "14:23:40", duration: "8.2 s",  detail: "5 dimensions evaluated. Technical timeline risk: 3/5 severity." },
  { id: "governance", name: "Governance",        status: "done",     time: "14:23:48", duration: "4.1 s",  detail: "Advisory: PROCEED with milestone gates." },
  { id: "approval",   name: "Approval",          status: "awaiting-human",                                 detail: "Awaiting your decision on the strategic recommendation." },
];

const COMPLETED_STAGES: TimelineStage[] = [
  { id: "customer",   name: "Customer Research", status: "done",     time: "14:22:01", duration: "38.4 s", detail: "87% confidence.",                                                          analystColor: "--ai-analyst-customer",  parallel: true },
  { id: "analytics",  name: "Product Analytics", status: "done",     time: "14:22:01", duration: "41.2 s", detail: "79% confidence.",                                                          analystColor: "--ai-analyst-analytics", parallel: true },
  { id: "market",     name: "Market",            status: "done",     time: "14:22:01", duration: "35.0 s", detail: "82% confidence.",                                                          analystColor: "--ai-analyst-market",    parallel: true },
  { id: "business",   name: "Business",          status: "done",     time: "14:22:01", duration: "29.3 s", detail: "73% confidence.",                                                          analystColor: "--ai-analyst-business",  parallel: true },
  { id: "technical",  name: "Technical",         status: "degraded", time: "14:22:01", duration: "44.1 s", detail: "Fell back to scenario evidence. 58% confidence.",                          analystColor: "--ai-analyst-technical", parallel: true },
  { id: "recall",     name: "Recall",            status: "done",     time: "14:22:01", duration: "1.1 s",  detail: "3 lessons injected.",                                                      parallel: true },
  { id: "debate",     name: "Debate",            status: "done",     time: "14:23:00", duration: "22.1 s", detail: "2 rounds complete. Advocate prevailed; Skeptic's risk noted." },
  { id: "strategist", name: "Strategist",        status: "done",     time: "14:23:22", duration: "11.8 s", detail: "Phased rollout with 20% user cohort. Revised once by Judge." },
  { id: "judge",      name: "Judge",             status: "done",     time: "14:23:34", duration: "6.4 s",  detail: "Evidence: 0.84 · Rationale: 0.79 — PASS." },
  { id: "risk",       name: "Risk",              status: "done",     time: "14:23:40", duration: "8.2 s",  detail: "Technical timeline at 3/5. Mitigation: staged delivery." },
  { id: "governance", name: "Governance",        status: "done",     time: "14:23:48", duration: "4.1 s",  detail: "Advisory: PROCEED." },
  { id: "approval",   name: "Approval",          status: "done",     time: "14:23:52", duration: "38.0 s", detail: "Approved by human operator." },
];

function ExecutionTimeline({
  stages,
  showApprovalActions = false,
  recommendation,
}: {
  stages: TimelineStage[];
  showApprovalActions?: boolean;
  recommendation?: { text: string; confidence: number };
}) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const rowRefs = useRef<(HTMLDivElement | null)[]>([]);

  const allParallel = stages.filter((s) => s.parallel);
  const sequential  = stages.filter((s) => !s.parallel);

  const toggle = (id: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });

  const handleKey = (e: RKE<HTMLDivElement>, idx: number, id: string, hasDetail: boolean) => {
    if (e.key === "ArrowDown") { e.preventDefault(); rowRefs.current[Math.min(idx + 1, stages.length - 1)]?.focus(); }
    if (e.key === "ArrowUp")   { e.preventDefault(); rowRefs.current[Math.max(idx - 1, 0)]?.focus(); }
    if ((e.key === "Enter" || e.key === " ") && hasDetail) { e.preventDefault(); toggle(id); }
  };

  const renderRow = (stage: TimelineStage, idx: number) => {
    const cfg       = STATUS_CFG[stage.status];
    const isExp     = expanded.has(stage.id);
    const hasDetail = Boolean(stage.detail);
    const isHuman   = stage.status === "awaiting-human";
    const style     = vars({
      "--p4b-tl-fill": `var(${cfg.fill})`,
      "--p4b-tl-text": `var(${cfg.text})`,
      ...(stage.analystColor ? { "--p4b-analyst-color": `var(${stage.analystColor})` } : {}),
    });

    return (
      <div
        key={stage.id}
        ref={(el) => { rowRefs.current[idx] = el; }}
        className={`p4b-tl-row${isHuman ? " p4b-tl-row--human" : ""}${cfg.live ? " p4b-tl-row--live" : ""}`}
        style={style}
        tabIndex={0}
        aria-expanded={hasDetail ? isExp : undefined}
        onKeyDown={(e) => handleKey(e, idx, stage.id, hasDetail)}
        onClick={() => hasDetail && toggle(stage.id)}
      >
        {stage.analystColor && <span className="p4b-tl-strip" aria-hidden="true" />}
        <span
          className={`p4b-tl-marker${cfg.live ? " p4b-tl-marker--live" : ""}`}
          aria-label={`${stage.name}: ${cfg.label}`}
        >
          {cfg.live
            ? <span className="p4b-tl-pulse" aria-hidden="true" />
            : <Icon name={cfg.icon} size="xs" />
          }
        </span>
        <div className="p4b-tl-content">
          <div className="p4b-tl-head">
            <span className="p4b-tl-name">{stage.name}</span>
            <StatusBadge status={stage.status} />
            {hasDetail && (
              <span className="p4b-tl-expand-icon" aria-hidden="true">
                <Icon name={isExp ? "chevron-down" : "chevron-right"} size="xs" />
              </span>
            )}
          </div>
          {isExp && stage.detail && <p className="p4b-tl-detail">{stage.detail}</p>}
          {isHuman && showApprovalActions && (
            <div className="p4b-tl-actions">
              <button className="p4b-btn p4b-btn--primary"   type="button">Approve</button>
              <button className="p4b-btn p4b-btn--danger"    type="button">Reject</button>
              <button className="p4b-btn p4b-btn--secondary" type="button">Request analysis</button>
            </div>
          )}
        </div>
        <div className="p4b-tl-meta">
          {stage.time     && <span className="p4b-tl-time">{stage.time}</span>}
          {stage.duration && <span className="p4b-tl-dur">{stage.duration}</span>}
        </div>
      </div>
    );
  };

  return (
    <div className="p4b-timeline" aria-label="Execution timeline">
      {/* Parallel group */}
      <div className="p4b-tl-parallel-group">
        <div className="p4b-tl-parallel-header">
          <span className="p4b-tl-parallel-label">Parallel</span>
          <span className="p4b-tl-parallel-count">{allParallel.length} agents</span>
        </div>
        <div className="p4b-tl-parallel-body">
          {allParallel.map((s, i) => renderRow(s, i))}
        </div>
      </div>

      {/* Join connector */}
      <div className="p4b-tl-join" aria-hidden="true" />

      {/* Sequential stages */}
      <div className="p4b-tl-sequential">
        {sequential.map((s, i) => renderRow(s, allParallel.length + i))}
      </div>

      {/* Completed result */}
      {recommendation && (
        <div className="p4b-tl-result">
          <div className="p4b-tl-result__head">
            <span className="p4b-tl-result__label">Recommendation</span>
            <ConfidenceBar value={recommendation.confidence} />
          </div>
          <p className="p4b-tl-result__text">{recommendation.text}</p>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════ 3. DEBATE TURN CARD ═══ */

function DebateTurnCard({
  round, roundTotal, advocateArg, skepticArg,
}: {
  round: number; roundTotal: number; advocateArg: string; skepticArg: string;
}) {
  return (
    <div className="p4b-debate-card">
      <div className="p4b-debate-card__round">Round {round} of {roundTotal}</div>
      <div className="p4b-debate-card__sides">
        <div className="p4b-debate-card__side p4b-debate-card__side--advocate">
          <div className="p4b-debate-card__side-head">
            <span className="p4b-debate-card__side-icon"><Icon name="scale" size="xs" /></span>
            <span className="p4b-debate-card__side-role">Advocate</span>
          </div>
          <p className="p4b-debate-card__arg">{advocateArg}</p>
        </div>
        <div className="p4b-debate-card__side p4b-debate-card__side--skeptic">
          <div className="p4b-debate-card__side-head">
            <span className="p4b-debate-card__side-icon"><Icon name="warning" size="xs" /></span>
            <span className="p4b-debate-card__side-role">Skeptic</span>
          </div>
          <p className="p4b-debate-card__arg">{skepticArg}</p>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════ 4. RECOMMENDATION CARD ═══ */

function RecommendationCard({
  recommendation, confidence, rationale, expectedOutcomes,
}: {
  recommendation: string; confidence: number; rationale: string; expectedOutcomes: string[];
}) {
  return (
    <div className="p4b-rec-card">
      <div className="p4b-rec-card__head">
        <span className="p4b-rec-card__label">
          <Icon name="sparkle" size="xs" />
          Recommendation
        </span>
        <ConfidenceBar value={confidence} />
      </div>
      <p className="p4b-rec-card__text">{recommendation}</p>
      <p className="p4b-rec-card__rationale">{rationale}</p>
      <ul className="p4b-rec-card__outcomes" role="list">
        {expectedOutcomes.map((o) => (
          <li key={o} className="p4b-rec-card__outcome">
            <Icon name="check" size="xs" />
            {o}
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ════════════════════════════════════════════════════ 5. JUDGMENT CARD ═══ */

function MiniScoreBar({ value, label }: { value: number; label: string }) {
  const tier = value < 0.4 ? "low" : value < 0.7 ? "medium" : "high";
  return (
    <div className="p4b-judgment-card__score">
      <span className="p4b-judgment-card__score-label">{label}</span>
      <span
        className="p4b-judgment-card__score-track"
        style={vars({
          "--p4b-judge-fill": `var(--ai-confidence-${tier})`,
          "--p4b-judge-pct":  `${Math.round(value * 100)}%`,
        })}
      >
        <span className="p4b-judgment-card__score-fill" />
      </span>
      <span className="p4b-judgment-card__score-val">{value.toFixed(2)}</span>
    </div>
  );
}

function JudgmentCard({
  evidenceScore, rationaleScore, verdict, critique,
}: {
  evidenceScore: number; rationaleScore: number; verdict: "pass" | "fail" | "retry"; critique?: string;
}) {
  return (
    <div className={`p4b-judgment-card p4b-judgment-card--${verdict}`}>
      <div className="p4b-judgment-card__head">
        <span className="p4b-judgment-card__label">
          <Icon name="scale" size="xs" /> Judge evaluation
        </span>
        <span className={`p4b-judgment-card__verdict p4b-judgment-card__verdict--${verdict}`}>
          {verdict.toUpperCase()}
        </span>
      </div>
      <div className="p4b-judgment-card__scores">
        <MiniScoreBar value={evidenceScore}  label="Evidence grounding" />
        <MiniScoreBar value={rationaleScore} label="Rationale coherence" />
      </div>
      {critique && <p className="p4b-judgment-card__critique">{critique}</p>}
    </div>
  );
}

/* ═══════════════════════════════════════════ 6. APPROVAL REQUEST CARD ═══ */

function ApprovalRequestCard({
  recommendation, confidence,
}: {
  recommendation: string; confidence: number;
}) {
  return (
    <div className="p4b-approval-card" role="region" aria-label="Human approval required">
      <div className="p4b-approval-card__head">
        <span className="p4b-approval-card__label">
          <Icon name="diamond" size="xs" />
          Awaiting your decision
        </span>
        <ConfidenceBar value={confidence} />
      </div>
      <p className="p4b-approval-card__text">{recommendation}</p>
      <div className="p4b-approval-card__actions">
        <button className="p4b-btn p4b-btn--primary"   type="button">Approve</button>
        <button className="p4b-btn p4b-btn--danger"    type="button">Reject</button>
        <button className="p4b-btn p4b-btn--secondary" type="button">Request analysis</button>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════ 7. EXECUTION PROGRESS ═══ */

function ExecutionProgress({
  completedStages, totalStages, currentStage, elapsed,
}: {
  completedStages: number; totalStages: number; currentStage: string; elapsed: string;
}) {
  const pct = Math.round((completedStages / totalStages) * 100);
  return (
    <div className="p4b-exec-progress">
      <div className="p4b-exec-progress__meta">
        <span className="p4b-exec-progress__stages">{completedStages} of {totalStages} stages</span>
        <span className="p4b-exec-progress__current">{currentStage}</span>
        <span className="p4b-exec-progress__elapsed">{elapsed} elapsed</span>
      </div>
      <div
        className="p4b-exec-progress__bar"
        style={vars({ "--p4b-prog-pct": `${pct}%` })}
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${completedStages} of ${totalStages} stages complete`}
      >
        <div className="p4b-exec-progress__fill" />
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════ 8. PARALLEL TASK VIEWER ═══ */

type MiniAgent = { name: string; status: AgentStatus; colorVar: string };

const MINI_AGENTS: MiniAgent[] = [
  { name: "Customer",  status: "done",    colorVar: "--ai-analyst-customer"  },
  { name: "Analytics", status: "done",    colorVar: "--ai-analyst-analytics" },
  { name: "Market",    status: "running", colorVar: "--ai-analyst-market"    },
  { name: "Business",  status: "waiting", colorVar: "--ai-analyst-business"  },
  { name: "Technical", status: "waiting", colorVar: "--ai-analyst-technical" },
];

function ParallelTaskViewer({ agents }: { agents: MiniAgent[] }) {
  return (
    <div className="p4b-parallel-viewer">
      <div className="p4b-parallel-viewer__label">Running in parallel</div>
      <div className="p4b-parallel-viewer__grid">
        {agents.map((a) => {
          const cfg = STATUS_CFG[a.status];
          return (
            <div
              key={a.name}
              className={`p4b-mini-agent${cfg.live ? " p4b-mini-agent--live" : ""}`}
              style={vars({ "--p4b-mini-color": `var(${a.colorVar})`, "--p4b-mini-fill": `var(${cfg.fill})` })}
            >
              <span className="p4b-mini-agent__dot" aria-hidden="true" />
              <span className="p4b-mini-agent__name">{a.name}</span>
              <StatusBadge status={a.status} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════ 9. RETRY CARD ═══ */

function RetryCard({
  attempt, maxAttempts, critique,
}: {
  attempt: number; maxAttempts: number; critique: string;
}) {
  return (
    <div className="p4b-retry-card">
      <div className="p4b-retry-card__head">
        <span className="p4b-retry-card__icon"><Icon name="refresh" size="xs" /></span>
        <span className="p4b-retry-card__label">Judge requested revision</span>
        <span className="p4b-retry-card__count">Attempt {attempt} of {maxAttempts}</span>
      </div>
      <p className="p4b-retry-card__critique">{critique}</p>
      <div className="p4b-retry-card__status">
        <span className="p4b-retry-card__status-dot" aria-hidden="true" />
        Strategist revising...
      </div>
    </div>
  );
}

/* ═════════════════════════════════════════════ 10. CANCELLATION BANNER ═══ */

function CancellationBanner({ completedStages, totalStages }: { completedStages: number; totalStages: number }) {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed) return null;
  return (
    <div className="p4b-cancel-banner" role="alert">
      <span className="p4b-cancel-banner__icon"><Icon name="ban" size="xs" /></span>
      <span className="p4b-cancel-banner__text">
        Run cancelled — {completedStages} of {totalStages} stages completed.
      </span>
      <button
        className="p4b-cancel-banner__dismiss"
        type="button"
        aria-label="Dismiss cancellation notice"
        onClick={() => setDismissed(true)}
      >
        <Icon name="x" size="xs" />
      </button>
    </div>
  );
}

/* ══════════════════════════════════════════════ 11. RESUME PANEL CARD ═══ */

function ResumePanelCard({ stage }: { stage: string }) {
  return (
    <div className="p4b-resume-card">
      <span className="p4b-resume-card__icon"><Icon name="diamond" size="sm" /></span>
      <div className="p4b-resume-card__body">
        <p className="p4b-resume-card__text">
          Run paused at the <strong>{stage}</strong> stage — awaiting your decision.
        </p>
        <button className="p4b-btn p4b-btn--primary" type="button">Resume and approve</button>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════ 12. LIVE LOG VIEWER ═══ */

type LogLevel = "trace" | "debug" | "info" | "warn" | "error" | "critical";

const LOG_ENTRIES: { ts: string; level: LogLevel; msg: string }[] = [
  { ts: "14:22:01.004", level: "info",     msg: "Session started · decision_pipeline v3" },
  { ts: "14:22:01.018", level: "debug",    msg: "Evidence source resolved: scenario=sample" },
  { ts: "14:22:01.031", level: "info",     msg: "Analysts dispatched in parallel (5 nodes)" },
  { ts: "14:22:04.210", level: "info",     msg: "customer_research: node complete (38.4 s)" },
  { ts: "14:22:05.113", level: "info",     msg: "product_analytics: node complete (41.2 s)" },
  { ts: "14:22:07.803", level: "warn",     msg: "market: connector unavailable, degrading to scenario" },
  { ts: "14:22:07.810", level: "info",     msg: "market: node complete (35.0 s) [DEGRADED]" },
  { ts: "14:22:08.442", level: "info",     msg: "business: node complete (29.3 s)" },
  { ts: "14:22:08.781", level: "error",    msg: "technical: store query timed out after 5 s" },
  { ts: "14:22:08.782", level: "warn",     msg: "technical: degrading to scenario evidence" },
];

function LiveLogViewer() {
  return (
    <div className="p4b-log-viewer">
      <div className="p4b-log-viewer__header">
        <span className="p4b-log-viewer__title">Event log</span>
        <span className="p4b-log-viewer__count">{LOG_ENTRIES.length} entries</span>
      </div>
      <div className="p4b-log-viewer__body" role="log" aria-label="Live event log" aria-live="polite">
        {LOG_ENTRIES.map((entry, i) => (
          <div key={i} className={`p4b-log-row p4b-log-row--${entry.level}`}>
            <span className="p4b-log-row__ts">{entry.ts}</span>
            <span className="p4b-log-row__level">{entry.level.toUpperCase()}</span>
            <span className="p4b-log-row__msg">{entry.msg}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════ 13. STREAMING CONSOLE ═══ */

type ConsoleLineKind = "info" | "warn" | "error" | "done" | "default";

const CONSOLE_LINES: { ts: string; kind: ConsoleLineKind; msg: string }[] = [
  { ts: "14:32:01", kind: "default", msg: "Starting decision pipeline..." },
  { ts: "14:32:01", kind: "info",    msg: "Evidence collected: scenario=sample" },
  { ts: "14:32:01", kind: "info",    msg: "Analysts dispatched in parallel (5 agents)..." },
  { ts: "14:32:03", kind: "done",    msg: "customer_research: done" },
  { ts: "14:32:04", kind: "done",    msg: "product_analytics: done" },
  { ts: "14:32:05", kind: "warn",    msg: "market: DEGRADED (fell back to scenario)" },
  { ts: "14:32:06", kind: "done",    msg: "business: done" },
  { ts: "14:32:06", kind: "done",    msg: "technical: done" },
  { ts: "14:32:07", kind: "info",    msg: "Debate starting (2 rounds)..." },
  { ts: "14:32:29", kind: "done",    msg: "debate: done" },
  { ts: "14:32:30", kind: "info",    msg: "Strategist synthesising recommendation..." },
  { ts: "14:32:42", kind: "warn",    msg: "judge: retry requested (evidence grounding 0.68 < 0.70)" },
  { ts: "14:32:49", kind: "done",    msg: "judge: PASS (evidence=0.84, rationale=0.79)" },
];

function StreamingConsole() {
  return (
    <div className="p4b-console">
      <div className="p4b-console__header">
        <span className="p4b-console__title">
          <Icon name="terminal" size="xs" />
          productagents run evaluate_initiative
        </span>
      </div>
      <div className="p4b-console__body" role="log" aria-label="Command output" aria-live="polite">
        {CONSOLE_LINES.map((line, i) => (
          <div key={i} className={`p4b-console__line p4b-console__line--${line.kind}`}>
            <span className="p4b-console__ts">[{line.ts}]</span>
            <span className="p4b-console__msg">{line.msg}</span>
          </div>
        ))}
        <div className="p4b-console__line p4b-console__line--default" aria-hidden="true">
          <span className="p4b-console__ts">[14:32:50]</span>
          <span className="p4b-console__msg"><span className="p4b-cursor" /></span>
        </div>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════ 14. TOOL EXECUTION CARD ═══ */

function ToolExecutionCard({
  toolName, args, status, resultSummary,
}: {
  toolName: string; args: string; status: AgentStatus; resultSummary?: string;
}) {
  const cfg = STATUS_CFG[status];
  return (
    <div
      className={`p4b-tool-card p4b-tool-card--${status}`}
      style={vars({ "--p4b-tool-fill": `var(${cfg.fill})` })}
    >
      <div className="p4b-tool-card__border" aria-hidden="true" />
      <div className="p4b-tool-card__body">
        <div className="p4b-tool-card__head">
          <span className="p4b-tool-card__icon"><Icon name="plug" size="xs" /></span>
          <span className="p4b-tool-card__name">{toolName}</span>
          <StatusBadge status={status} />
        </div>
        <p className="p4b-tool-card__args">{args}</p>
        {resultSummary && <p className="p4b-tool-card__result">{resultSummary}</p>}
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════ 15. TOOL CALL INSPECTOR ═══ */

function ToolCallInspector({
  toolName, args, response, duration,
}: {
  toolName: string; args: string; response: string; duration: string;
}) {
  return (
    <details className="p4b-tool-inspector">
      <summary className="p4b-tool-inspector__trigger">
        <span className="p4b-tool-inspector__icon"><Icon name="tool" size="xs" /></span>
        <span className="p4b-tool-inspector__name">{toolName}</span>
        <span className="p4b-tool-inspector__dur">{duration}</span>
        <span className="p4b-tool-inspector__chevron" aria-hidden="true">
          <Icon name="chevron-right" size="xs" />
        </span>
      </summary>
      <div className="p4b-tool-inspector__body">
        <div className="p4b-tool-inspector__section">
          <span className="p4b-tool-inspector__label">Arguments</span>
          <pre className="p4b-tool-inspector__code">{args}</pre>
        </div>
        <div className="p4b-tool-inspector__section">
          <span className="p4b-tool-inspector__label">Response preview</span>
          <pre className="p4b-tool-inspector__code">{response}</pre>
        </div>
      </div>
    </details>
  );
}

/* ══════════════════════════════════════════════════════════ GALLERY ═══════ */

export function Phase4Execution() {
  return (
    <>
      <div className="sg-subband">
        <h3>4B · Execution & Streaming Reasoning</h3>
        <span>
          The execution view and streaming reasoning components — the centrepiece of the
          ProductAgents design system. The ExecutionTimeline makes the full decision pipeline
          legible in real time: parallel analysts, debate dialectic, judge scores, and the
          human-approval step in one glanceable view.
        </span>
      </div>

      {/* 1. EXECUTION CARD ───────────────────────────────────────────────────── */}
      <Section
        id="p4b-exec-card"
        title="Execution card"
        desc="Summary card for one run: status colour-bar on the left edge, initiative title, workflow name, timing, and a confidence bar. Status is reinforced by colour + badge."
      >
        <div className="sg-card p4b-stack">
          <Specimen label="running">
            <ExecutionCard
              title="Adopt usage-based pricing tier"
              status="running"
              workflow="evaluate_initiative"
              startedAt="14:22:01"
            />
          </Specimen>
          <Specimen label="completed with confidence">
            <ExecutionCard
              title="Sunset legacy mobile SDK v2"
              status="done"
              workflow="evaluate_initiative"
              startedAt="14:10:50"
              duration="2 m 41 s"
              confidence={82}
            />
          </Specimen>
          <Specimen label="degraded">
            <ExecutionCard
              title="Expand to EU data residency"
              status="degraded"
              workflow="evaluate_initiative"
              startedAt="13:55:22"
              duration="3 m 02 s"
              confidence={58}
            />
          </Specimen>
          <Specimen label="failed">
            <ExecutionCard
              title="Prioritise SSO for enterprise tier"
              status="failed"
              workflow="evaluate_initiative"
              startedAt="14:18:12"
              duration="0 m 22 s"
            />
          </Specimen>
        </div>
      </Section>

      {/* 2. EXECUTION TIMELINE ───────────────────────────────────────────────── */}
      <Section
        id="p4b-exec-timeline"
        title="Execution timeline"
        desc="Full pipeline timeline: 5 parallel analysts + Recall in a bracketed group, then Debate, Strategist, Judge, Risk, Governance, Approval sequentially. Arrow keys navigate stages; Enter/Space expand detail. Three specimen states: mid-run, approval-pending (pulsing indigo border), completed."
      >
        <div className="sg-card p4b-stack">
          <Specimen label="mid-run — analysts in parallel, debate live">
            <ExecutionTimeline stages={MID_RUN_STAGES} />
          </Specimen>
          <Specimen label="approval pending — pipeline complete, awaiting human (pulsing indigo)">
            <ExecutionTimeline stages={APPROVAL_STAGES} showApprovalActions />
          </Specimen>
          <Specimen label="completed — approved, recommendation shown">
            <ExecutionTimeline
              stages={COMPLETED_STAGES}
              recommendation={{
                text: "Launch the initiative with a phased rollout, beginning with a 20% user cohort and expanding on milestone verification.",
                confidence: 82,
              }}
            />
          </Specimen>
        </div>
      </Section>

      {/* 3. DEBATE TURN CARD ─────────────────────────────────────────────────── */}
      <Section
        id="p4b-debate-card"
        title="Debate turn card"
        desc="One debate round: Advocate (teal, case FOR) vs Skeptic (amber, case AGAINST). Split two-column layout makes the dialectic immediately legible. Label + icon distinguish each voice beyond colour."
      >
        <div className="sg-card p4b-stack">
          <Specimen label="round 1 of 2">
            <DebateTurnCard
              round={1}
              roundTotal={2}
              advocateArg="Customer feedback volume is highest in the past 6 quarters. Three independent cohorts confirm willingness-to-pay for the proposed feature. The market window is open now."
              skepticArg="Analytics show that power users — 8% of the base — drive 61% of revenue. The proposed change risks churn in that segment before adequate mitigation measures are in place."
            />
          </Specimen>
          <Specimen label="round 2 of 2">
            <DebateTurnCard
              round={2}
              roundTotal={2}
              advocateArg="A phased rollout to 20% of users caps the power-user risk while validating the hypothesis. Historical data shows this segment adapts quickly when change is communicated in advance."
              skepticArg="The phased plan lacks defined rollback criteria. Without a measurable exit condition, the rollout could stall at 20% indefinitely. Governance should require explicit success thresholds."
            />
          </Specimen>
        </div>
      </Section>

      {/* 4. RECOMMENDATION CARD ──────────────────────────────────────────────── */}
      <Section
        id="p4b-rec-card"
        title="Recommendation card"
        desc="Strategist output: the recommendation text, confidence bar, the rationale paragraph, and expected outcomes as a checkmark list. The confidence gauge is the signature instrument motif."
      >
        <div className="sg-card">
          <RecommendationCard
            recommendation="Launch the initiative with a phased rollout, beginning with a 20% user cohort. Expand on verified milestone outcomes at 30 and 60 days."
            confidence={82}
            rationale="All five analysts concur on opportunity validity. The primary risk — power-user churn — is bounded by the phased approach. Three prior decisions with similar profiles showed positive long-term outcomes after milestone-gated rollouts."
            expectedOutcomes={[
              "Retention improves by 8–12% in the target cohort within 60 days",
              "Power-user churn held below 2% by proactive communication",
              "Revenue uplift of 15–20% on the pilot cohort at 90-day mark",
            ]}
          />
        </div>
      </Section>

      {/* 5. JUDGMENT CARD ────────────────────────────────────────────────────── */}
      <Section
        id="p4b-judgment-card"
        title="Judgment card"
        desc="Judge node output: two calibrated score bars (evidence grounding, rationale coherence), a PASS/RETRY/FAIL verdict badge, and an optional critique used when a retry is triggered."
      >
        <div className="sg-card p4b-stack">
          <Specimen label="pass">
            <JudgmentCard evidenceScore={0.84} rationaleScore={0.79} verdict="pass" />
          </Specimen>
          <Specimen label="retry — critique shown">
            <JudgmentCard
              evidenceScore={0.68}
              rationaleScore={0.74}
              verdict="retry"
              critique="The evidence grounding score (0.68) falls below the required threshold of 0.70. The recommendation references market timing without citing the specific analyst data that supports it. Revise the rationale to trace each claim back to a named analyst finding."
            />
          </Specimen>
          <Specimen label="fail">
            <JudgmentCard evidenceScore={0.41} rationaleScore={0.38} verdict="fail" critique="Both dimensions below threshold after maximum retries. Run degraded gracefully." />
          </Specimen>
        </div>
      </Section>

      {/* 6. APPROVAL REQUEST CARD ────────────────────────────────────────────── */}
      <Section
        id="p4b-approval-card"
        title="Approval request card"
        desc="Human-in-the-loop card shown when the pipeline pauses at Governance. Pulsing indigo border demands attention; three actions: Approve, Reject, Request analysis. Confidence bar gives context."
      >
        <div className="sg-card">
          <ApprovalRequestCard
            recommendation="Launch the initiative with a phased rollout, beginning with a 20% user cohort. Expand on verified milestone outcomes at 30 and 60 days."
            confidence={82}
          />
        </div>
      </Section>

      {/* 7. EXECUTION PROGRESS ───────────────────────────────────────────────── */}
      <Section
        id="p4b-exec-progress"
        title="Execution progress"
        desc="Overall run progress bar with stage count, current stage name, and elapsed time. The fill uses the same teal done-colour as stage markers. Semantic progressbar with aria-valuenow."
      >
        <div className="sg-card p4b-stack">
          <Specimen label="early run">
            <ExecutionProgress completedStages={3} totalStages={12} currentStage="Market analyst" elapsed="0 m 38 s" />
          </Specimen>
          <Specimen label="mid run">
            <ExecutionProgress completedStages={7} totalStages={12} currentStage="Strategist" elapsed="2 m 01 s" />
          </Specimen>
          <Specimen label="nearly done">
            <ExecutionProgress completedStages={11} totalStages={12} currentStage="Approval" elapsed="2 m 41 s" />
          </Specimen>
        </div>
      </Section>

      {/* 8. PARALLEL TASK VIEWER ─────────────────────────────────────────────── */}
      <Section
        id="p4b-parallel-viewer"
        title="Parallel task viewer"
        desc="Compact grid showing the five analysts as mini-agent cells during parallel execution. Each cell has a status dot, name, and badge. Running agents animate amber; done agents show teal."
      >
        <div className="sg-card">
          <ParallelTaskViewer agents={MINI_AGENTS} />
        </div>
      </Section>

      {/* 9. RETRY CARD ───────────────────────────────────────────────────────── */}
      <Section
        id="p4b-retry-card"
        title="Retry card"
        desc="Shown when the Judge triggers a Strategist revision. Displays attempt count, the critique the Strategist must address, and a live status indicator while revision runs."
      >
        <div className="sg-card">
          <RetryCard
            attempt={1}
            maxAttempts={1}
            critique="Evidence grounding score 0.68 falls below the 0.70 threshold. The recommendation references market timing without citing the specific analyst data that supports it. Trace each claim back to a named finding."
          />
        </div>
      </Section>

      {/* 10. CANCELLATION BANNER ─────────────────────────────────────────────── */}
      <Section
        id="p4b-cancel-banner"
        title="Cancellation banner"
        desc="role=alert banner shown when a run is cancelled mid-flight. Shows how many stages completed before cancellation. Dismissible with the X button."
      >
        <div className="sg-card">
          <CancellationBanner completedStages={4} totalStages={12} />
        </div>
      </Section>

      {/* 11. RESUME PANEL CARD ───────────────────────────────────────────────── */}
      <Section
        id="p4b-resume-card"
        title="Resume panel card"
        desc="Shown in the Runs list when a pipeline is paused at a human-approval interrupt. The pulsing diamond icon echoes the awaiting-human state; the primary action resumes and shows the approval UI."
      >
        <div className="sg-card">
          <ResumePanelCard stage="Governance" />
        </div>
      </Section>

      {/* 12. LIVE LOG VIEWER ─────────────────────────────────────────────────── */}
      <Section
        id="p4b-log-viewer"
        title="Live log viewer"
        desc="Scrollable event log with timestamps, level badges, and message text. Levels use --ai-log-* tokens: info=blue, warn=amber, error=red, debug=slate. role=log with aria-live for screen readers."
      >
        <div className="sg-card">
          <LiveLogViewer />
        </div>
      </Section>

      {/* 13. STREAMING CONSOLE ───────────────────────────────────────────────── */}
      <Section
        id="p4b-console"
        title="Streaming console"
        desc="Terminal-style panel mirroring the CLI output. Plex Mono, dark surface regardless of theme, timestamped lines coloured by kind. A blinking cursor shows the active position."
      >
        <div className="sg-card">
          <StreamingConsole />
        </div>
      </Section>

      {/* 14. TOOL EXECUTION CARD ─────────────────────────────────────────────── */}
      <Section
        id="p4b-tool-card"
        title="Tool execution card"
        desc="Compact card for one connector/tool call: tool name, status badge, argument preview, and result summary on completion. The left colour-bar matches the tool status."
      >
        <div className="sg-card p4b-stack">
          <Specimen label="running">
            <ToolExecutionCard
              toolName="github.list_issues"
              args='{"owner": "mcapanema", "repo": "ProductAgents", "state": "open", "limit": 50}'
              status="running"
            />
          </Specimen>
          <Specimen label="done">
            <ToolExecutionCard
              toolName="jira.search_issues"
              args='{"jql": "project = PA AND type = Bug AND created >= -30d", "fields": ["summary", "priority"]}'
              status="done"
              resultSummary="Returned 23 issues. 8 high-priority bugs surfaced in the feedback corpus."
            />
          </Specimen>
          <Specimen label="failed">
            <ToolExecutionCard
              toolName="github.list_issues"
              args='{"owner": "mcapanema", "repo": "ProductAgents", "state": "open"}'
              status="failed"
              resultSummary="HTTP 401 Unauthorized — token expired or missing scope."
            />
          </Specimen>
        </div>
      </Section>

      {/* 15. TOOL CALL INSPECTOR ─────────────────────────────────────────────── */}
      <Section
        id="p4b-tool-inspector"
        title="Tool call inspector"
        desc="Expandable details element for deep-inspecting a tool call. Collapsed: tool name + duration. Expanded: full arguments JSON and response preview. Uses native <details> for zero-JS disclosure."
      >
        <div className="sg-card p4b-stack">
          <Specimen label="collapsed / expanded">
            <ToolCallInspector
              toolName="github.list_issues"
              duration="1.4 s"
              args={`{\n  "owner": "mcapanema",\n  "repo": "ProductAgents",\n  "state": "open",\n  "limit": 50\n}`}
              response={`[\n  { "number": 42, "title": "Add EU data residency option", "state": "open" },\n  { "number": 41, "title": "Streaming reasoning view", "state": "open" },\n  ... 48 more\n]`}
            />
          </Specimen>
          <Specimen label="error response">
            <ToolCallInspector
              toolName="jira.search_issues"
              duration="0.8 s"
              args={`{\n  "jql": "project = PA AND type = Bug",\n  "fields": ["summary", "priority"]\n}`}
              response={`{\n  "error": "401 Unauthorized",\n  "message": "Token is invalid or has expired"\n}`}
            />
          </Specimen>
        </div>
      </Section>
    </>
  );
}
