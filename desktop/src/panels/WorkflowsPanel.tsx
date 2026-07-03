import { useEffect, useState } from "react";
import { useIpc } from "../app/IpcProvider";
import type { WorkflowSummary } from "../ipc/types";
import { EmptyState } from "../ui/EmptyState";
import { EmptyStateIcon } from "../ui/emptyStateIcons";

export function WorkflowsPanel() {
  const ipc = useIpc();
  const [list, setList] = useState<WorkflowSummary[]>([]);

  useEffect(() => {
    if (ipc) ipc.workflowsList().then(setList).catch(() => setList([]));
  }, [ipc]);

  return (
    <div>
      <h1>Workflows</h1>
      <p className="page-desc">Registered decision pipelines available to run.</p>
      {list.length === 0 && (
        <EmptyState
          title="No workflows registered"
          description="Workflows are defined in the platform registry. None are available in this workspace yet."
          icon={<EmptyStateIcon name="workflows" />}
        />
      )}
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
