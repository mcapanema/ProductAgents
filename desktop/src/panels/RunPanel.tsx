import { useReducer, useState } from "react";
import { useIpc } from "../app/IpcProvider";
import { runReducer, initialRunState } from "./runReducer";

export function RunPanel() {
  const ipc = useIpc();
  const [title, setTitle] = useState("");
  const [evidence, setEvidence] = useState("sample");
  const [state, dispatch] = useReducer(runReducer, initialRunState);

  async function start() {
    if (!ipc || !title.trim()) return;
    dispatch({ kind: "start" });
    try {
      const result = await ipc.run(
        { workflow: "evaluate_initiative", title, evidence },
        { onEvent: (event) => dispatch({ kind: "event", event }) },
      );
      dispatch({ kind: "done", result });
    } catch (err) {
      dispatch({ kind: "error", message: err instanceof Error ? err.message : String(err) });
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
      </div>
      {state.status !== "idle" && (
        <p className="muted">
          Status: {state.status}
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
