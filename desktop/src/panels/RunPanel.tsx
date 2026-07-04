import { useEffect, useReducer, useState } from "react";
import { Alert, Button, Checkbox, Input } from "antd";
import { useIpc } from "../app/IpcProvider";
import { runReducer, initialRunState } from "./runReducer";
import { deriveStages } from "./runTimeline";
import { StageTimeline } from "./StageTimeline";
import { RawEvents } from "./RawEvents";
import { EmptyState } from "../ui/EmptyState";
import { EmptyStateIcon } from "../ui/emptyStateIcons";
import "./RunPanel.css";

const VERDICTS: { verdict: string; label: string }[] = [
  { verdict: "approve", label: "Approve" },
  { verdict: "reject", label: "Reject" },
  { verdict: "request_analysis", label: "Request analysis" },
];

export function RunPanel({ onRunningChange }: { onRunningChange?: (running: boolean) => void }) {
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
  useEffect(() => {
    onRunningChange?.(running);
  }, [running, onRunningChange]);
  return (
    <div>
      <h1>Run a decision</h1>
      <p className="page-desc">Evaluate an initiative through the advisory pipeline.</p>
      <div className="row run-controls">
        <Input
          aria-label="initiative"
          placeholder="Initiative title…"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onPressEnter={start}
          className="run-controls__title"
        />
        <Input
          aria-label="evidence"
          placeholder="evidence (scenario or path)"
          value={evidence}
          onChange={(e) => setEvidence(e.target.value)}
          onPressEnter={start}
          className="run-controls__evidence"
        />
        <Button type="primary" onClick={start} loading={running} disabled={running || !ipc}>
          Run
        </Button>
        {running && !state.awaiting && (
          <Button onClick={cancel} loading={state.cancelling} disabled={!state.sessionId || state.cancelling}>
            Cancel
          </Button>
        )}
      </div>
      <div className="row run-controls">
        <Checkbox
          checked={approval}
          onChange={(e) => setApproval(e.target.checked)}
          disabled={running}
        >
          Require approval (human-in-the-loop)
        </Checkbox>
      </div>
      {state.awaiting && (
        <div className="approval">
          <p className="approval__title">Approval needed</p>
          {state.advisory && (
            <p className="approval__advisory">Advisory recommendation: {state.advisory.verdict}</p>
          )}
          <div className="row">
            {VERDICTS.map((v) => (
              <Button key={v.verdict} onClick={() => decide(v.verdict)}>
                {v.label}
              </Button>
            ))}
          </div>
        </div>
      )}
      {state.error && (
        <Alert className="run-alert" type="error" showIcon message="Run failed" description={state.error} />
      )}
      {state.status !== "idle" && (
        <p className="muted run-status">
          Status: {state.awaiting ? "awaiting approval" : state.status}
          {state.sessionId ? ` · session ${state.sessionId}` : ""}
        </p>
      )}
      {state.status === "idle" && (
        <EmptyState
          title="Ready when you are"
          description="Enter an initiative title and evidence source, then Run. Progress and the final verdict stream in here."
          icon={<EmptyStateIcon name="run" />}
        />
      )}
      {state.events.length > 0 && (
        <>
          <StageTimeline stages={deriveStages(state.events)} />
          <RawEvents events={state.events} />
        </>
      )}
    </div>
  );
}
