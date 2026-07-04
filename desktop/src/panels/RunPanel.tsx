import { useEffect, useReducer, useState } from "react";
import { Button, Checkbox, Input, Select } from "antd";
import { useIpc } from "../app/IpcProvider";
import { runReducer, initialRunState } from "./runReducer";
import { deriveStages } from "./runTimeline";
import { StageTimeline } from "./StageTimeline";
import { RawEvents } from "./RawEvents";
import { EmptyState } from "../ui/EmptyState";
import { EmptyStateIcon } from "../ui/emptyStateIcons";
import type { WorkflowSummary } from "../ipc/types";

const VERDICTS: { verdict: string; label: string }[] = [
  { verdict: "approve", label: "Approve" },
  { verdict: "reject", label: "Reject" },
  { verdict: "request_analysis", label: "Request analysis" },
];

// ponytail: no separate WorkflowSummary[] "loading" state — an empty list is
// itself the degrade-to-literal state (see the Select's options fallback below).
const FALLBACK_WORKFLOW = "evaluate_initiative";

export function RunPanel({ onRunningChange }: { onRunningChange?: (running: boolean) => void }) {
  const ipc = useIpc();
  const [title, setTitle] = useState("");
  const [evidence, setEvidence] = useState("sample");
  const [approval, setApproval] = useState(false);
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [workflow, setWorkflow] = useState(FALLBACK_WORKFLOW);
  const [state, dispatch] = useReducer(runReducer, initialRunState);

  // Fetch the registered workflows once on mount and preselect the default
  // (fallback: the first entry). A client without `workflowsList` (older IPC,
  // or a partial fake in tests) or a failed call just leaves the literal
  // fallback selected — degrade, don't crash.
  useEffect(() => {
    if (!ipc?.workflowsList) return;
    ipc
      .workflowsList()
      .then((wfs) => {
        setWorkflows(wfs);
        const def = wfs.find((w) => w.is_default) ?? wfs[0];
        if (def) setWorkflow(def.name);
      })
      .catch(() => setWorkflows([]));
  }, [ipc]);

  async function start() {
    if (!ipc || !title.trim()) return;
    dispatch({ kind: "start" });
    try {
      const result = await ipc.run(
        { workflow, title, evidence, approval },
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
      <div className="row" style={{ marginBottom: 8 }}>
        <Select
          aria-label="Workflow"
          value={workflow}
          onChange={setWorkflow}
          style={{ width: 220 }}
          disabled={running}
          options={
            workflows.length > 0
              ? workflows.map((w) => ({ value: w.name, label: w.is_default ? `★ ${w.title}` : w.title }))
              : [{ value: FALLBACK_WORKFLOW, label: FALLBACK_WORKFLOW }]
          }
        />
        <Input
          aria-label="initiative"
          placeholder="Initiative title…"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          style={{ flex: 1 }}
        />
        <Input
          aria-label="evidence"
          placeholder="evidence (scenario or path)"
          value={evidence}
          onChange={(e) => setEvidence(e.target.value)}
          style={{ width: 220 }}
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
      <div className="row" style={{ gap: 6, marginBottom: 8 }}>
        <Checkbox
          checked={approval}
          onChange={(e) => setApproval(e.target.checked)}
          disabled={running}
        >
          Require approval (human-in-the-loop)
        </Checkbox>
      </div>
      {state.awaiting && (
        <div className="approval" style={{ marginBottom: 12 }}>
          <p>
            Approval needed
            {state.advisory ? ` · advisory: ${state.advisory.verdict}` : ""}
          </p>
          <div className="row" style={{ gap: 8 }}>
            {VERDICTS.map((v) => (
              <Button key={v.verdict} onClick={() => decide(v.verdict)}>
                {v.label}
              </Button>
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
