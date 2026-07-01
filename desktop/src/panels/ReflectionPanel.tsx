import { useEffect, useState } from "react";
import { Button, Input, Select } from "antd";
import { useIpc } from "../app/IpcProvider";
import type { DecisionSummary, OutcomeRecord } from "../ipc/types";
import { formatConfidence } from "./decisionView";

export function ReflectionPanel() {
  const ipc = useIpc();
  const [decisions, setDecisions] = useState<DecisionSummary[]>([]);
  const [selected, setSelected] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<OutcomeRecord | null>(null);

  useEffect(() => {
    if (!ipc) return;
    ipc
      .decisionsList()
      .then((rows) => {
        setDecisions(rows);
        if (rows[0]) setSelected(rows[0].id);
      })
      .catch(() => setDecisions([]));
  }, [ipc]);

  async function submit() {
    if (!ipc || !selected || !note.trim()) return;
    setBusy(true);
    setOutcome(null);
    try {
      setOutcome(await ipc.reflectionRecord(selected, note.trim()));
    } catch {
      setOutcome(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>Reflection</h1>
      {decisions.length === 0 && <p className="muted">No decisions to reflect on yet.</p>}
      {decisions.length > 0 && (
        <div style={{ maxWidth: 560 }}>
          <label className="field">
            <span>Decision</span>
            <Select
              aria-label="decision"
              value={selected}
              onChange={setSelected}
              style={{ width: "100%" }}
              options={decisions.map((d) => ({ value: d.id, label: `${d.title} — ${d.recommendation}` }))}
            />
          </label>
          <label className="field">
            <span>What happened?</span>
            <Input.TextArea
              aria-label="what happened"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={4}
            />
          </label>
          <Button type="primary" onClick={submit} loading={busy} disabled={busy || !ipc}>
            Reflect
          </Button>
          {outcome && (
            <div style={{ marginTop: 16 }}>
              <p>Prediction accuracy: {formatConfidence(outcome.prediction_accuracy)}</p>
              <h3>Actual outcomes</h3>
              <ul>
                {outcome.actual_outcomes.map((o, i) => (
                  <li key={i}>{o}</li>
                ))}
              </ul>
              <h3>Lessons learned</h3>
              <ul>
                {outcome.lessons_learned.map((l, i) => (
                  <li key={i}>{l}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
