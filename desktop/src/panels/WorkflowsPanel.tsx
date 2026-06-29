import { useEffect, useState } from "react";
import { useIpc } from "../app/IpcProvider";
import type { WorkflowSummary } from "../ipc/types";

export function WorkflowsPanel() {
  const ipc = useIpc();
  const [list, setList] = useState<WorkflowSummary[]>([]);

  useEffect(() => {
    if (ipc) ipc.workflowsList().then(setList).catch(() => setList([]));
  }, [ipc]);

  return (
    <div>
      <h1>Workflows</h1>
      {list.length === 0 && <p className="muted">No workflows registered.</p>}
      {list.map((w) => (
        <div className="list-item" key={w.name}>
          <div>
            <strong>{w.title}</strong> <span className="muted">({w.name})</span>
          </div>
          <div className="muted">{w.description}</div>
        </div>
      ))}
    </div>
  );
}
