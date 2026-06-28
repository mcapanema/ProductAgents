import { useEffect, useState } from "react";
import { useIpc } from "../app/IpcProvider";
import type { DecisionDetail, DecisionSummary } from "../ipc/types";
import { formatConfidence, predictionRows } from "./decisionView";

export function DecisionsPanel() {
  const ipc = useIpc();
  const [list, setList] = useState<DecisionSummary[]>([]);
  const [detail, setDetail] = useState<DecisionDetail | null>(null);

  useEffect(() => {
    if (ipc) ipc.decisionsList().then(setList).catch(() => setList([]));
  }, [ipc]);

  async function open(id: string) {
    if (!ipc) return;
    try {
      setDetail(await ipc.decisionsShow(id));
    } catch {
      setDetail(null);
    }
  }

  return (
    <div>
      <h1>Decision Explorer</h1>
      {list.length === 0 && <p className="muted">No decisions recorded yet.</p>}
      <div className="row" style={{ alignItems: "flex-start", gap: 24 }}>
        <div style={{ flex: "0 0 320px" }}>
          {list.map((d) => (
            <div className="list-item" key={d.id} onClick={() => open(d.id)}>
              <div>{d.title}</div>
              <div className="muted">
                {d.recommendation} · {formatConfidence(d.confidence)} · {d.created_at}
              </div>
            </div>
          ))}
        </div>
        {detail && <DecisionDetailView detail={detail} />}
      </div>
    </div>
  );
}

function DecisionDetailView({ detail }: { detail: DecisionDetail }) {
  const rows = predictionRows(detail);
  const rec = detail.record.recommendation;
  return (
    <div style={{ flex: 1 }}>
      <h2 style={{ marginTop: 0 }}>{detail.record.initiative.title}</h2>
      <p>
        <strong>{rec.recommendation}</strong> · {formatConfidence(rec.confidence)}
      </p>
      <p className="muted">{rec.rationale}</p>
      <h3>Predicted outcomes</h3>
      <ul>{rows.predicted.map((o, i) => <li key={i}>{o}</li>)}</ul>
      <h3>Actual outcomes</h3>
      {rows.actual.length ? (
        <ul>{rows.actual.map((o, i) => <li key={i}>{o}</li>)}</ul>
      ) : (
        <p className="muted">No reflection recorded yet.</p>
      )}
      <h3>Lessons learned</h3>
      {rows.lessons.length ? (
        <ul>{rows.lessons.map((o, i) => <li key={i}>{o}</li>)}</ul>
      ) : (
        <p className="muted">—</p>
      )}
    </div>
  );
}
