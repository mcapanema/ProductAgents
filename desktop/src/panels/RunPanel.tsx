import { useReducer, useState } from "react";
import { useIpc } from "../app/IpcProvider";
import { runReducer, initialRunState } from "./runReducer";

const VERDICTS: { verdict: string; label: string }[] = [
  { verdict: "approve", label: "Approve" },
  { verdict: "reject", label: "Reject" },
  { verdict: "request_analysis", label: "Request analysis" },
];

export function RunPanel() {
  const ipc = useIpc();
  const [title, setTitle] = useState("");
  const [evidence, setEvidence] = useState("sample");
  const [approval, setApproval] = useState(false);
  const [state, dispatch] = useReducer(runReducer, initialRunState);

  async function start() {
    if (!ipc || !title.trim()) return;
    dispatch({ kind: "start" });
    try {
      const result = await ipc.run(
        { workflow: "evaluate_initiative", title, evidence, approval },
        { onEvent: (event) => dispatch({ kind: "event", event }) },
      );
      dispatch({ kind: "done", result });
    } catch (err) {
      dispatch({ kind: "error", message: err instanceof Error ? err.message : String(err) });
    }
  }

  async function decide(verdict: string) {
    if (!ipc) return;
    dispatch({ kind: "approved" });
    try {
      await ipc.approve(verdict, "");
    } catch {
      // the run will surface failure via its terminal result/error
    }
  }

  async function cancel() {
    if (!ipc || !state.sessionId) return;
    dispatch({ kind: "cancel" });
    try {
      await ipc.runCancel(state.sessionId);
    } catch {
      // terminal result/error will surface the outcome
    }
  }

  const running = state.status === "running";
  return (
    <div>
      <h1>Run a decision</h1>
      <div className="row" style={{ marginBottom: 8 }}>
        <input
          aria-label="initiative"
          placeholder="Initiative title…"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          style={{ flex: 1 }}
        />
        <input
          aria-label="evidence"
          placeholder="evidence (scenario or path)"
          value={evidence}
          onChange={(e) => setEvidence(e.target.value)}
          style={{ width: 220 }}
        />
        <button className="primary" onClick={start} disabled={running || !ipc}>
          {running ? "Running…" : "Run"}
        </button>
        {running && !state.awaiting && (
          <button onClick={cancel} disabled={!state.sessionId || state.cancelling}>
            {state.cancelling ? "Cancelling…" : "Cancel"}
          </button>
        )}
      </div>
      <label className="row" style={{ gap: 6, marginBottom: 8 }}>
        <input
          type="checkbox"
          checked={approval}
          onChange={(e) => setApproval(e.target.checked)}
          disabled={running}
        />
        <span>Require approval (human-in-the-loop)</span>
      </label>
      {state.awaiting && (
        <div className="approval" style={{ marginBottom: 12 }}>
          <p>
            Approval needed
            {state.advisory ? ` · advisory: ${state.advisory.verdict}` : ""}
          </p>
          <div className="row" style={{ gap: 8 }}>
            {VERDICTS.map((v) => (
              <button key={v.verdict} onClick={() => decide(v.verdict)}>
                {v.label}
              </button>
            ))}
          </div>
        </div>
      )}
      {state.status !== "idle" && (
        <p className="muted">
          Status: {state.awaiting ? "awaiting approval" : state.status}
          {state.sessionId ? ` · session ${state.sessionId}` : ""}
          {state.error ? ` · ${state.error}` : ""}
        </p>
      )}
      <div>
        {state.events.map((event, i) => (
          <div className="event" key={i}>
            <strong>{event.type}</strong>{" "}
            <span className="muted">{JSON.stringify(event.payload)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
