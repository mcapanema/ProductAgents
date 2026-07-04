import { useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { RightOutlined } from "@ant-design/icons";
import type { StageDetail, StageState, StageStatus } from "../ipc/events";
import { nodeKind, KIND_META } from "./workflowNodeKinds";
import { ConfidenceGauge } from "../ui/ConfidenceGauge";
import "./StageTimeline.css";

// The 5 analysts + recall fan out concurrently from START; everything after is sequential.
const PARALLEL = new Set<string>(["customer_research", "product_analytics", "market", "business", "technical", "recall"]);
const AI: Record<StageStatus, string> = { pending: "waiting", running: "running", done: "done", failed: "failed" };
const WORD: Record<StageStatus, string> = { pending: "queued", running: "running", done: "done", failed: "failed" };

export function StageTimeline({ stages }: { stages: StageState[] }) {
  // The active stage: the one currently running, else the furthest one that has settled.
  const activeKey = useMemo(() => {
    let running: string | null = null;
    let settled: string | null = null;
    for (const s of stages) {
      if (s.status === "running") running = s.key;
      if (s.status === "done" || s.status === "failed") settled = s.key;
    }
    return running ?? settled ?? null;
  }, [stages]);

  const [overrides, setOverrides] = useState<Record<string, boolean>>({});
  const isOpen = (key: string) => overrides[key] ?? key === activeKey;
  const toggle = (key: string) => setOverrides((o) => ({ ...o, [key]: !isOpen(key) }));

  // Keep the active stage in view as the run advances (motion-safe).
  const activeRef = useRef<HTMLLIElement | null>(null);
  useEffect(() => {
    const el = activeRef.current;
    if (!el || typeof el.scrollIntoView !== "function") return; // jsdom has no scrollIntoView
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    el.scrollIntoView({ block: "nearest", behavior: reduce ? "auto" : "smooth" });
  }, [activeKey]);

  const parallel = stages.filter((s) => PARALLEL.has(s.key));
  const sequential = stages.filter((s) => !PARALLEL.has(s.key));
  const active = stages.find((s) => s.key === activeKey);

  const row = (s: StageState) => (
    <StageRow
      key={s.key}
      stage={s}
      open={isOpen(s.key)}
      onToggle={() => toggle(s.key)}
      rowRef={s.key === activeKey ? activeRef : undefined}
      active={s.key === activeKey}
    />
  );

  return (
    <div className="run-tl">
      <p className="run-tl__live" aria-live="polite">
        {active ? `${active.label}: ${WORD[active.status]}` : ""}
      </p>
      {parallel.length > 0 && (
        <>
          <div className="run-tl__group-head">
            <span className="run-tl__group-label">Parallel analysis</span>
            <span className="run-tl__group-count">{parallel.length}</span>
          </div>
          <ul className="run-tl__list run-tl__parallel">{parallel.map(row)}</ul>
        </>
      )}
      <ul className="run-tl__list run-tl__seq">{sequential.map(row)}</ul>
    </div>
  );
}

function StageRow({
  stage,
  open,
  onToggle,
  rowRef,
  active,
}: {
  stage: StageState;
  open: boolean;
  onToggle: () => void;
  rowRef?: React.Ref<HTMLLIElement>;
  active: boolean;
}) {
  const meta = KIND_META[nodeKind(stage.key)];
  const Icon = meta.icon;
  const summary = stageSummary(stage.detail);
  const detail = stageDetail(stage.detail);
  const style = {
    "--stage-accent": `var(${meta.colorToken})`,
    "--stage-status": `var(--ai-${AI[stage.status]})`,
    "--stage-status-text": stage.status === "pending" ? "var(--text-tertiary)" : `var(--ai-${AI[stage.status]}-text)`,
  } as CSSProperties;

  return (
    <li ref={rowRef} className="run-tl__row" data-status={stage.status} data-active={active} style={style}>
      <button
        type="button"
        className="run-tl__head"
        aria-expanded={detail ? open : undefined}
        disabled={!detail}
        onClick={onToggle}
      >
        <span className="run-tl__marker" aria-hidden><Icon /></span>
        <span className="run-tl__id">
          <span className="run-tl__role">{meta.role}</span>
          <span className="run-tl__label">{stage.label}</span>
        </span>
        <span className="run-tl__end">
          {summary && <span className="run-tl__summary">{summary}</span>}
          <span className="run-tl__status">{WORD[stage.status]}</span>
          {detail && <RightOutlined className="run-tl__chevron" aria-hidden />}
        </span>
      </button>
      {detail && open && <div className="run-tl__detail">{detail}</div>}
    </li>
  );
}

const count = (n: number, one: string) => `${n} ${one}${n === 1 ? "" : "s"}`;

// Collapsed headline — the result, always visible (traceability); depth is the detail.
function stageSummary(d: StageDetail): ReactNode {
  switch (d.kind) {
    case "recommendation":
      return d.recommendation && (
        <>
          <strong>{d.recommendation.recommendation}</strong> <ConfidenceGauge value={d.recommendation.confidence} />
        </>
      );
    case "judge":
      return d.judged.passed ? "passed" : "failed";
    case "governance":
      return <strong>{d.verdict}</strong>;
    case "final":
      return (
        <>
          <strong>{d.verdict}</strong> · {d.decidedBy}
        </>
      );
    case "debate":
      return d.turns.length ? count(d.turns.length, "turn") : null;
    case "risk":
      return d.rows.length ? count(d.rows.length, "review") : null;
    case "recall":
      return d.lessons.length ? count(d.lessons.length, "lesson") : null;
    case "analyst":
      return d.report ? count(d.report.findings.length, "finding") : null;
    default:
      return null;
  }
}

function stageDetail(d: StageDetail): ReactNode {
  switch (d.kind) {
    case "analyst":
      if (!d.report) return null;
      return (
        <>
          <ul>{d.report.findings.map((f, i) => <li key={i}>{f}</li>)}</ul>
          {d.report.signals.length > 0 && <p className="muted">{d.report.signals.join(" · ")}</p>}
        </>
      );
    case "recall":
      return d.lessons.length ? <ul>{d.lessons.map((l, i) => <li key={i}>{l}</li>)}</ul> : null;
    case "debate":
      return d.turns.length ? (
        <>
          {d.turns.map((t, i) => (
            <div
              key={i}
              className="run-tl__turn"
              style={{ "--turn-color": /advoc/i.test(t.side) ? "var(--ai-advocate)" : "var(--ai-skeptic)" } as CSSProperties}
            >
              <span className="run-tl__side">R{t.round} · {t.side}</span>
              <p>{t.argument}</p>
            </div>
          ))}
        </>
      ) : null;
    case "recommendation":
      return d.recommendation ? <p className="muted">{d.recommendation.rationale}</p> : null;
    case "judge":
      return (
        <>
          <div className="run-tl__scores">
            <span className="run-tl__score">
              <span className="run-tl__score-label">Grounding</span>
              <ConfidenceGauge value={d.judged.evidence_grounding_score} label="Evidence grounding" />
            </span>
            <span className="run-tl__score">
              <span className="run-tl__score-label">Coherence</span>
              <ConfidenceGauge value={d.judged.rationale_coherence_score} label="Rationale coherence" />
            </span>
          </div>
          {d.judged.critique && <p className="muted">{d.judged.critique}</p>}
        </>
      );
    case "risk":
      return d.rows.length ? (
        <>
          {d.rows.map((r, i) => (
            <p key={i}>
              <strong>{r.level}</strong> · {r.reviewer}: <span className="muted">{r.rationale}</span>
            </p>
          ))}
        </>
      ) : null;
    case "governance":
      return d.rationale ? <p className="muted">{d.rationale}</p> : null;
    case "final":
      return d.rationale ? <p className="muted">{d.rationale}</p> : null;
    default:
      return null;
  }
}
