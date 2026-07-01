import { useEffect, useState } from "react";
import { List } from "antd";
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
      <List
        dataSource={list}
        rowKey="name"
        renderItem={(w) => (
          <List.Item>
            <List.Item.Meta title={w.title} description={w.description} />
          </List.Item>
        )}
      />
    </div>
  );
}
