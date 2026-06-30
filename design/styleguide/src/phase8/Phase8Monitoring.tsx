// design/styleguide/src/phase8/Phase8Monitoring.tsx
// Phase 8 — Monitoring & observability. Event Timeline, Metrics Card, Resource/
// Memory/Token Usage, Execution Statistics, Cost Dashboard, Performance Graph,
// Health Indicator. Grounded in the real Event Store / Session shapes
// (productagents.platform.events.Event subclasses + Session.id/workflow/status/
// created_at) where a backend shape exists today; per-event latency is computed
// from the real `ts` field. Token usage / memory / cost have no schema yet — those
// are forward-looking, built to the same session/seq identifiers so wiring is
// additive when a metrics source lands (see the doc's grounding note).
//
// Distinct from Phase 4B's Execution Timeline: 4B visualizes the LIVE, in-flight
// pipeline stage-by-stage (the streaming run replacing the raw-JSON dump). This
// Event Timeline is the persisted, full-fidelity log of a session's Event Store
// rows (every event type, seq-ordered) for after-the-fact audit — SessionService
// .events(), not the live graph stream.
//
// Built only from the existing token layer (no new colors); reuses the
// `--timeline-*` and `--gauge-*` component tokens Phase 2 reserved for exactly
// this. Icons are inline SVG (viewBox 0 0 24 24, stroke currentColor,
// stroke-width 1.75, round caps), defined locally as in every prior phase.
import type { CSSProperties, ReactNode } from "react";
import type { Density } from "../sg";
import { Section, Specimen } from "../sg";
import "./phase8-monitoring.css";

const vars = (v: Record<string, string | number>): CSSProperties => v as CSSProperties;

// ─────────────────────────────────────────────────────────────────── Icon ───
type IconName =
  | "activity" | "check-circle" | "x-circle" | "alert-triangle" | "alert-circle"
  | "flag" | "shield" | "user-check" | "message-square" | "play" | "slash"
  | "clock" | "trending-up" | "trending-down" | "minus" | "cpu" | "hash"
  | "dollar-sign" | "zap" | "heart-pulse" | "help-circle";

const ICON_PATHS: Record<IconName, ReactNode> = {
  activity: <path d="M3 12h4l2 7 4-14 2 7h6" />,
  "check-circle": <><circle cx="12" cy="12" r="8.5" /><path d="M8.5 12.5l2.3 2.3L16 9.5" /></>,
  "x-circle": <><circle cx="12" cy="12" r="8.5" /><path d="M9 9l6 6M15 9l-6 6" /></>,
  "alert-triangle": <><path d="M12 4.2l9 15.6H3z" /><path d="M12 10v4" /><path d="M12 16.8h.01" /></>,
  "alert-circle": <><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5v5" /><path d="M12 16h.01" /></>,
  flag: <><path d="M5 21V4" /><path d="M5 4h13l-3 4 3 4H5" /></>,
  shield: <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" />,
  "user-check": <><circle cx="9.5" cy="8" r="3.3" /><path d="M3.5 20c.7-3.5 3.2-5.5 6-5.5s5.3 2 6 5.5" /><path d="M16 11l1.7 1.7L21.5 9" /></>,
  "message-square": <path d="M4 5h16v11H8l-4 4V5z" />,
  play: <path d="M7 4.5l12 7.5-12 7.5V4.5z" />,
  slash: <><circle cx="12" cy="12" r="8.5" /><path d="M6.5 17.5l11-11" /></>,
  clock: <><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5v5l3.2 1.8" /></>,
  "trending-up": <><path d="M4 16l6-6 4 4 6-7" /><path d="M15 6.5h5V11" /></>,
  "trending-down": <><path d="M4 8l6 6 4-4 6 7" /><path d="M15 16.5h5V12" /></>,
  minus: <path d="M5 12h14" />,
  cpu: <><rect x="7" y="7" width="10" height="10" rx="1.5" /><path d="M9.5 7V3.5M14.5 7V3.5M9.5 20.5V17M14.5 20.5V17M17 9.5h3.5M17 14.5h3.5M3.5 9.5H7M3.5 14.5H7" /></>,
  hash: <path d="M5 9h14M5 15h14M10 4L8 20M16 4l-2 16" />,
  "dollar-sign": <><path d="M12 2.5v19" /><path d="M16.5 6.8c0-1.8-2-2.8-4.5-2.8s-4.5 1.1-4.5 3 1.8 2.6 4.5 3.1c2.7.5 4.5 1.3 4.5 3.2s-2 3-4.5 3-4.5-1-4.5-2.8" /></>,
  zap: <path d="M13 2L4 14h6l-1 8 9-12h-6l1-8z" />,
  "heart-pulse": <path d="M12 20.5S3.5 14.8 3.5 9a4.6 4.6 0 018.5-2.4A4.6 4.6 0 0120.5 9c0 1.3-.4 2.5-1 3.5H16l-1.8-3-2.4 6-1.8-3.5H8" />,
  "help-circle": <><circle cx="12" cy="12" r="8.5" /><path d="M9.6 9.3a2.4 2.4 0 014.6.9c0 1.6-2.2 1.8-2.2 3.3" /><path d="M12 17h.01" /></>,
};

function Icon({ name, size = "sm" }: { name: IconName; size?: "xs" | "sm" | "md" }) {
  return (
    <svg className={`p8-ico p8-ico--${size}`} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round"
      aria-hidden="true">
      {ICON_PATHS[name]}
    </svg>
  );
}

// ───────────────────────────────────────────────────────── Event Timeline ───
// Mirrors productagents.platform.events.Event subclasses 1:1 — one row kind per
// dataclass. seq/ts are the real EventStore/Session columns (SessionService
// .events() return order); `label`/`detail` are the human-readable rendering of
// each dataclass's real fields (node, round/side, level, passed, verdict, ...).
type EventKind =
  | "session_started" | "node_progress" | "analyst_completed" | "debate_turn"
  | "risk_assessed" | "judged" | "governance_advised" | "approval_requested"
  | "final_verdict" | "node_failed" | "session_failed" | "session_cancelled"
  | "session_finished";

interface SessionEvent {
  seq: number;
  ts: string;
  kind: EventKind;
  label: string;
  detail?: string;
}

const EVENT_META: Record<EventKind, { icon: IconName; tone: string }> = {
  session_started: { icon: "play", tone: "var(--text-tertiary)" },
  node_progress: { icon: "activity", tone: "var(--ai-running)" },
  analyst_completed: { icon: "check-circle", tone: "var(--ai-done)" },
  debate_turn: { icon: "message-square", tone: "var(--ai-advocate)" },
  risk_assessed: { icon: "alert-triangle", tone: "var(--signal)" },
  judged: { icon: "shield", tone: "var(--accent)" },
  governance_advised: { icon: "flag", tone: "var(--accent)" },
  approval_requested: { icon: "user-check", tone: "var(--ai-awaiting-human)" },
  final_verdict: { icon: "flag", tone: "var(--ai-done)" },
  node_failed: { icon: "alert-circle", tone: "var(--ai-failed)" },
  session_failed: { icon: "x-circle", tone: "var(--danger)" },
  session_cancelled: { icon: "slash", tone: "var(--text-tertiary)" },
  session_finished: { icon: "check-circle", tone: "var(--success)" },
};

const SAMPLE_EVENTS: SessionEvent[] = [
  { seq: 0, ts: "10:02:01", kind: "session_started", label: "Session started", detail: "evaluate_initiative" },
  { seq: 1, ts: "10:02:03", kind: "node_progress", label: "customer_research running" },
  { seq: 2, ts: "10:02:04", kind: "node_progress", label: "market running" },
  { seq: 3, ts: "10:02:09", kind: "analyst_completed", label: "customer_research completed" },
  { seq: 4, ts: "10:02:12", kind: "analyst_completed", label: "market completed" },
  { seq: 5, ts: "10:02:18", kind: "debate_turn", label: "Round 1 · advocate", detail: "Evidence supports the initiative" },
  { seq: 6, ts: "10:02:24", kind: "debate_turn", label: "Round 1 · skeptic", detail: "Sample size is thin" },
  { seq: 7, ts: "10:02:31", kind: "risk_assessed", label: "Risk: medium", detail: "Market timing reviewer" },
  { seq: 8, ts: "10:02:36", kind: "judged", label: "Judged · pass", detail: "attempt 1, grounding 0.82" },
  { seq: 9, ts: "10:02:38", kind: "governance_advised", label: "Governance: approve" },
  { seq: 10, ts: "10:02:39", kind: "approval_requested", label: "Awaiting human approval" },
  { seq: 11, ts: "10:03:02", kind: "session_finished", label: "Session finished" },
];

function EventTimeline({ events }: { events: SessionEvent[] }) {
  return (
    <ol className="p8-timeline" aria-label="Session event log">
      {events.map((e) => {
        const meta = EVENT_META[e.kind];
        return (
          <li key={e.seq} className="p8-timeline__row">
            <span className="p8-timeline__node" style={vars({ "--p8-tl-color": meta.tone })}>
              <Icon name={meta.icon} size="xs" />
            </span>
            <div className="p8-timeline__body">
              <div className="p8-timeline__head">
                <span className="p8-timeline__label">{e.label}</span>
                <span className="p8-timeline__ts">{e.ts}</span>
              </div>
              {e.detail && <p className="p8-timeline__detail">{e.detail}</p>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

// ─────────────────────────────────────────────────────────── Metrics Card ───
// Extends Phase 3D's Stat Card (`dd-stat`) with a threshold tier for monitoring
// values that need an ok/warning/critical read, not just an up/down delta. For
// a plain value+delta metric, use Phase 3D's Stat Card directly — this is not a
// replacement for it.
type MetricTier = "ok" | "warning" | "critical" | "neutral";

const TIER_META: Record<MetricTier, { tone: string; word: string }> = {
  ok: { tone: "var(--text-success)", word: "Normal" },
  warning: { tone: "var(--text-warning)", word: "Elevated" },
  critical: { tone: "var(--text-error)", word: "Critical" },
  neutral: { tone: "var(--text-tertiary)", word: "—" },
};

function MetricTile(props: { label: string; value: string; icon: IconName; tier?: MetricTier; deltaPct?: number }) {
  const tier = props.tier ?? "neutral";
  const meta = TIER_META[tier];
  return (
    <div className="p8-metric" data-tier={tier}>
      <div className="p8-metric__head">
        <Icon name={props.icon} size="sm" />
        <span className="p8-metric__label">{props.label}</span>
      </div>
      <div className="p8-metric__value">{props.value}</div>
      <div className="p8-metric__foot">
        <span className="p8-metric__tier" style={vars({ "--p8-tier-color": meta.tone })}>{meta.word}</span>
        {props.deltaPct != null && (
          <span className="p8-metric__delta" data-dir={props.deltaPct > 0 ? "up" : props.deltaPct < 0 ? "down" : "flat"}>
            <Icon name={props.deltaPct > 0 ? "trending-up" : props.deltaPct < 0 ? "trending-down" : "minus"} size="xs" />
            {Math.abs(props.deltaPct)}%
          </span>
        )}
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────── Resource/Memory/Token Usage ─
// No metrics endpoint exists yet (no token/memory schema in pa-core or the
// platform event vocabulary) — forward-looking, sized to the same gauge tokens
// Phase 4C's per-call Token Usage Bar already uses (`--gauge-*`). This is the
// session-aggregate counterpart: total usage across a run, not one LLM call.
function UsageGauge(props: { label: string; icon: IconName; used: number; total: number; unit: string }) {
  const pct = Math.min(100, Math.round((props.used / props.total) * 100));
  const tier: MetricTier = pct >= 90 ? "critical" : pct >= 70 ? "warning" : "ok";
  return (
    <div className="p8-usage">
      <div className="p8-usage__head">
        <span className="p8-usage__label"><Icon name={props.icon} size="xs" /> {props.label}</span>
        <span className="p8-usage__reading">{props.used.toLocaleString()} / {props.total.toLocaleString()} {props.unit}</span>
      </div>
      <div className="p8-usage__track" role="progressbar" aria-label={props.label}
        aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className="p8-usage__fill" data-tier={tier} style={vars({ "--p8-usage-pct": `${pct}%` })} />
      </div>
      <span className="p8-usage__pct" data-tier={tier}>{pct}% — {TIER_META[tier].word}</span>
    </div>
  );
}

// ───────────────────────────────────────────────────── Execution Statistics ─
// Grounded: node count / total events come straight off the SAMPLE_EVENTS log;
// avg latency is computed from the real `ts` deltas between consecutive events
// (the only timing signal the Event Store actually persists today).
function computeLatencies(events: SessionEvent[]): number[] {
  const toSec = (ts: string) => {
    const [h, m, s] = ts.split(":").map(Number);
    return h * 3600 + m * 60 + s;
  };
  const out: number[] = [];
  for (let i = 1; i < events.length; i++) out.push(toSec(events[i].ts) - toSec(events[i - 1].ts));
  return out;
}

function ExecutionStatistics({ events }: { events: SessionEvent[] }) {
  const latencies = computeLatencies(events);
  const avg = Math.round(latencies.reduce((a, b) => a + b, 0) / latencies.length);
  const nodeCount = new Set(events.filter((e) => e.kind === "node_progress" || e.kind === "analyst_completed").map((e) => e.label)).size;
  const rounds = events.filter((e) => e.kind === "debate_turn").length;
  return (
    <div className="p8-grid">
      <MetricTile label="Total events" value={String(events.length)} icon="hash" tier="neutral" />
      <MetricTile label="Nodes touched" value={String(nodeCount)} icon="cpu" tier="neutral" />
      <MetricTile label="Avg event latency" value={`${avg}s`} icon="clock" tier={avg > 20 ? "warning" : "ok"} />
      <MetricTile label="Debate turns" value={String(rounds)} icon="message-square" tier="neutral" />
    </div>
  );
}

// ───────────────────────────────────────────────────────────── Cost Dashboard ─
// No cost schema exists yet (no $ tracking anywhere in the platform) —
// forward-looking, shaped around the same node identifiers the real event
// vocabulary already uses so wiring is additive once a cost source lands.
interface CostLine { node: string; usd: number; }

function CostDashboard({ lines }: { lines: CostLine[] }) {
  const total = lines.reduce((a, l) => a + l.usd, 0);
  return (
    <div className="p8-cost">
      <div className="p8-cost__total">
        <Icon name="dollar-sign" size="md" />
        <span className="p8-cost__total-value">${total.toFixed(2)}</span>
        <span className="p8-cost__total-label">this session</span>
      </div>
      <ul className="p8-cost__list">
        {lines.map((l) => (
          <li key={l.node} className="p8-cost__row">
            <span className="p8-cost__node">{l.node}</span>
            <div className="p8-cost__bar-track">
              <div className="p8-cost__bar-fill" style={vars({ "--p8-cost-pct": `${Math.round((l.usd / total) * 100)}%` })} />
            </div>
            <span className="p8-cost__amount">${l.usd.toFixed(2)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ──────────────────────────────────────────────────────────── Performance Graph
// Grounded: plots the same real per-event `ts` deltas Execution Statistics
// summarizes, point by point. Inline SVG line chart (no charting dependency,
// matching every prior phase). Accessible per ui-ux-pro-max chart guidance:
// legend + axis labels + gridlines + a visible data-table fallback (disclosure)
// + an aria-label summary, so the trend isn't color-only or chart-only.
function PerformanceGraph({ events }: { events: SessionEvent[] }) {
  const latencies = computeLatencies(events);
  const max = Math.max(...latencies, 1);
  const w = 480, h = 140, pad = 28;
  const stepX = (w - pad * 2) / (latencies.length - 1);
  const points = latencies.map((v, i) => {
    const x = pad + i * stepX;
    const y = h - pad - (v / max) * (h - pad * 2);
    return { x, y, v, seq: i + 1 };
  });
  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  const summary = `Inter-event latency across ${latencies.length} event gaps, from ${Math.min(...latencies)}s to ${max}s, averaging ${Math.round(latencies.reduce((a, b) => a + b, 0) / latencies.length)}s.`;

  return (
    <div className="p8-perf">
      <div className="p8-perf__legend">
        <span className="p8-perf__legend-item"><span className="p8-perf__swatch" /> Inter-event latency (s)</span>
      </div>
      <svg className="p8-perf__svg" viewBox={`0 0 ${w} ${h}`} role="img" aria-label={summary}>
        {[0, 0.5, 1].map((f) => (
          <line key={f} className="p8-perf__grid" x1={pad} x2={w - pad}
            y1={h - pad - f * (h - pad * 2)} y2={h - pad - f * (h - pad * 2)} />
        ))}
        <line className="p8-perf__axis" x1={pad} y1={h - pad} x2={w - pad} y2={h - pad} />
        <path className="p8-perf__line" d={path} fill="none" />
        {points.map((p) => (
          <circle key={p.seq} className="p8-perf__point" cx={p.x} cy={p.y} r={3.5} tabIndex={0}
            aria-label={`Event ${p.seq}: ${p.v}s`}>
            <title>{`Event ${p.seq}: ${p.v}s`}</title>
          </circle>
        ))}
        <text className="p8-perf__axis-label" x={pad} y={h - 6}>seq 1</text>
        <text className="p8-perf__axis-label" x={w - pad} y={h - 6} textAnchor="end">{`seq ${latencies.length}`}</text>
      </svg>
      <details className="p8-perf__table-toggle">
        <summary>View as table</summary>
        <table className="p8-perf__table">
          <caption className="sr-only">Inter-event latency by sequence</caption>
          <thead><tr><th scope="col">Seq</th><th scope="col">Latency (s)</th></tr></thead>
          <tbody>
            {points.map((p) => <tr key={p.seq}><td>{p.seq}</td><td>{p.v}</td></tr>)}
          </tbody>
        </table>
      </details>
    </div>
  );
}

// ─────────────────────────────────────────────────────────── Health Indicator
// Generalizes Phase 6's `p6-health` (which is GitHub-connector-specific:
// healthy/degraded/error) to any monitored subject keyed off Session.status
// plus whether a NodeFailed/SessionFailed/SessionCancelled occurred along the
// way. For a connector's health specifically, prefer Phase 6's RepositoryCard.
type HealthState = "healthy" | "degraded" | "error" | "running" | "idle" | "unknown";

const HEALTH_META: Record<HealthState, { icon: IconName; tone: string; word: string }> = {
  healthy: { icon: "heart-pulse", tone: "var(--text-success)", word: "Healthy" },
  degraded: { icon: "alert-triangle", tone: "var(--text-warning)", word: "Degraded" },
  error: { icon: "x-circle", tone: "var(--text-error)", word: "Error" },
  running: { icon: "activity", tone: "var(--ai-running-text)", word: "Running" },
  idle: { icon: "clock", tone: "var(--text-tertiary)", word: "Idle" },
  unknown: { icon: "help-circle", tone: "var(--text-tertiary)", word: "Unknown" },
};

function HealthIndicator({ state, subject }: { state: HealthState; subject: string }) {
  const meta = HEALTH_META[state];
  return (
    <span className="p8-health" data-state={state}>
      <span className="p8-health__dot" style={vars({ "--p8-health-color": meta.tone })} aria-hidden="true" />
      <Icon name={meta.icon} size="xs" />
      <span className="p8-health__subject">{subject}</span>
      <span className="p8-health__word">{meta.word}</span>
    </span>
  );
}

// ──────────────────────────────────────────────────────────────── Gallery ───
const COST_LINES: CostLine[] = [
  { node: "customer_research", usd: 0.41 },
  { node: "market", usd: 0.38 },
  { node: "debate", usd: 0.92 },
  { node: "strategist", usd: 0.27 },
  { node: "judge", usd: 0.18 },
];

export function Phase8Monitoring({ density }: { density: Density }) {
  return (
    <div className="p8-root" data-density={density}>
      <Section id="p8-event-timeline" title="Event Timeline"
        desc="Persisted Event Store log for one session — every Event subclass, seq-ordered. The audit/observability view; Phase 4B owns the live in-flight pipeline view.">
        <Specimen label="default"><EventTimeline events={SAMPLE_EVENTS} /></Specimen>
      </Section>

      <Section id="p8-metrics-card" title="Metrics Card"
        desc="A threshold-tiered stat tile for monitoring values. Extends Phase 3D's Stat Card — use that one directly for plain value+delta metrics.">
        <Specimen label="tiers">
          <div className="p8-grid">
            <MetricTile label="Sessions today" value="14" icon="activity" tier="ok" deltaPct={8} />
            <MetricTile label="Judge pass rate" value="91%" icon="check-circle" tier="ok" deltaPct={-2} />
            <MetricTile label="Avg debate rounds" value="2.3" icon="message-square" tier="neutral" />
            <MetricTile label="Failed sessions" value="1" icon="alert-circle" tier="warning" deltaPct={100} />
          </div>
        </Specimen>
      </Section>

      <Section id="p8-resource-usage" title="Resource / Memory / Token Usage"
        desc="Session-aggregate usage gauges. No metrics source exists yet — forward-looking, sized to the same --gauge-* tokens Phase 4C's per-call Token Usage Bar uses.">
        <Specimen label="default">
          <div className="p8-stack">
            <UsageGauge label="Context tokens" icon="hash" used={142_000} total={200_000} unit="tok" />
            <UsageGauge label="Memory" icon="cpu" used={780} total={1024} unit="MB" />
            <UsageGauge label="Vector store" icon="cpu" used={96} total={100} unit="MB" />
          </div>
        </Specimen>
      </Section>

      <Section id="p8-execution-statistics" title="Execution Statistics"
        desc="Aggregate counts for one session, computed from its real Event Store rows (event count, node count, ts-delta latency, debate turns).">
        <Specimen label="default"><ExecutionStatistics events={SAMPLE_EVENTS} /></Specimen>
      </Section>

      <Section id="p8-cost-dashboard" title="Cost Dashboard"
        desc="Per-node $ breakdown for one session. No cost schema exists yet — forward-looking, keyed off the same node identifiers the real event vocabulary uses.">
        <Specimen label="default"><CostDashboard lines={COST_LINES} /></Specimen>
      </Section>

      <Section id="p8-performance-graph" title="Performance Graph"
        desc="Inter-event latency over a session, from real ts deltas. Legend, gridlines, axis labels, per-point tooltips, and a table fallback — never color-only.">
        <Specimen label="default"><PerformanceGraph events={SAMPLE_EVENTS} /></Specimen>
      </Section>

      <Section id="p8-health-indicator" title="Health Indicator"
        desc="Compact status badge keyed off Session.status (+ whether a NodeFailed/SessionFailed occurred). Generalizes Phase 6's connector-specific p6-health.">
        <Specimen label="states">
          <div className="p8-row">
            <HealthIndicator state="healthy" subject="evaluate_initiative" />
            <HealthIndicator state="running" subject="evaluate_initiative" />
            <HealthIndicator state="degraded" subject="evaluate_initiative" />
            <HealthIndicator state="error" subject="evaluate_initiative" />
            <HealthIndicator state="idle" subject="evaluate_initiative" />
            <HealthIndicator state="unknown" subject="evaluate_initiative" />
          </div>
        </Specimen>
      </Section>
    </div>
  );
}
