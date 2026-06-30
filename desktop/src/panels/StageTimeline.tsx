import type { StageDetail, StageState, StageStatus } from "../ipc/events";
import { formatConfidence } from "./decisionView";

const GLYPH: Record<StageStatus, string> = {
  pending: "◌",
  running: "◐",
  done: "✓",
  failed: "⚠",
};

export function StageTimeline({ stages }: { stages: StageState[] }) {
  return (
    <div className="timeline">
      {stages.map((s) => (
        <details key={s.key} className="list-item" data-status={s.status}>
          <summary className="row" style={{ gap: 8, cursor: "pointer", listStyle: "none" }}>
            <span aria-hidden>{GLYPH[s.status]}</span>
            <span>{s.label}</span>
            <span className="muted" style={{ marginLeft: "auto" }}>{s.status}</span>
          </summary>
          <div style={{ paddingTop: 6 }}>
            <StageDetailView detail={s.detail} />
          </div>
        </details>
      ))}
    </div>
  );
}

function StageDetailView({ detail }: { detail: StageDetail }) {
  switch (detail.kind) {
    case "analyst":
      if (!detail.report) return null;
      return (
        <>
          <ul style={{ margin: "4px 0", paddingLeft: 18 }}>
            {detail.report.findings.map((f, i) => <li key={i}>{f}</li>)}
          </ul>
          {detail.report.signals.length > 0 && (
            <p className="muted">{detail.report.signals.join(" · ")}</p>
          )}
        </>
      );
    case "debate":
      return (
        <>
          {detail.turns.map((t, i) => (
            <p key={i}><strong>R{t.round} {t.side}:</strong> {t.argument}</p>
          ))}
        </>
      );
    case "recall":
      return (
        <ul style={{ margin: "4px 0", paddingLeft: 18 }}>
          {detail.lessons.map((l, i) => <li key={i}>{l}</li>)}
        </ul>
      );
    case "recommendation":
      if (!detail.recommendation) return null;
      return (
        <>
          <p><strong>{detail.recommendation.recommendation}</strong> · <span>{formatConfidence(detail.recommendation.confidence)}</span></p>
          <p className="muted">{detail.recommendation.rationale}</p>
        </>
      );
    case "judge":
      return (
        <p className="muted">
          {detail.judged.passed ? "passed" : "failed"} · grounding {detail.judged.evidence_grounding_score} · coherence {detail.judged.rationale_coherence_score}
          {detail.judged.critique ? ` · ${detail.judged.critique}` : ""}
        </p>
      );
    case "risk":
      return (
        <>
          {detail.rows.map((r, i) => (
            <p key={i}><strong>{r.level}</strong> · {r.reviewer}: <span className="muted">{r.rationale}</span></p>
          ))}
        </>
      );
    case "governance":
      return <p><strong>{detail.verdict}</strong> · <span className="muted">{detail.rationale}</span></p>;
    case "final":
      return <p><strong>{detail.verdict}</strong> ({detail.decidedBy}) · <span className="muted">{detail.rationale}</span></p>;
    default:
      return <p className="muted">—</p>;
  }
}
