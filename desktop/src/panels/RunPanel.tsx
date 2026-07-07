import { useEffect, useState } from "react";
import { Alert, Button, Checkbox, Input } from "antd";
import { useIpc } from "../app/IpcProvider";
import { useRun } from "../app/RunContext";
import { deriveStages } from "./runTimeline";
import { StageTimeline } from "./StageTimeline";
import { RawEvents } from "./RawEvents";
import { EmptyState } from "../ui/EmptyState";
import { EmptyStateIcon } from "../ui/emptyStateIcons";
import { WorkflowSelect } from "./WorkflowSelect";
import type { WorkflowSummary } from "../ipc/types";
import "./RunPanel.css";

const VERDICTS: { verdict: string; label: string }[] = [
  { verdict: "approve", label: "Approve" },
  { verdict: "reject", label: "Reject" },
  { verdict: "request_analysis", label: "Request analysis" },
];

export function RunPanel() {
  const ipc = useIpc();
  const { state, start: startRun, decide, cancel } = useRun();
  const [title, setTitle] = useState("");
  const [evidence, setEvidence] = useState("sample");
  const [approval, setApproval] = useState(false);
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [workflow, setWorkflow] = useState("evaluate_initiative");

  // Load the registered workflows so the user can pick which to run. Guarded:
  // some tests inject a client without workflowsList — degrade to the default.
  useEffect(() => {
    if (!ipc?.workflowsList) return;
    ipc
      .workflowsList()
      .then((wfs) => {
        setWorkflows(wfs);
        if (wfs.length > 0) setWorkflow(wfs[0].name);
      })
      .catch(() => setWorkflows([]));
  }, [ipc]);

  function start() {
    if (!title.trim()) return;
    startRun({ workflow, title, evidence, approval });
  }

  const running = state.status === "running";
  return (
    <div>
      <h1>Run a decision</h1>
      <p className="page-desc">
        {workflows.find((w) => w.name === workflow)?.description ??
          "Evaluate an initiative through the advisory pipeline."}
      </p>
      <div className="row run-controls">
        <WorkflowSelect
          workflows={workflows}
          value={workflow}
          onChange={setWorkflow}
          disabled={running}
        />
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
