import { useEffect, useState } from "react";
import { Background, ReactFlow, type Edge, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useIpc } from "../app/IpcProvider";
import type { WorkflowDetail, WorkflowNode, WorkflowSummary } from "../ipc/types";
import { layoutTopology, nodeLabel } from "./workflowView";
import { NodePromptDrawer } from "./NodePromptDrawer";
import { EmptyState } from "../ui/EmptyState";
import { EmptyStateIcon } from "../ui/emptyStateIcons";

export function WorkflowsPanel() {
  const ipc = useIpc();
  const [list, setList] = useState<WorkflowSummary[]>([]);
  const [detail, setDetail] = useState<WorkflowDetail | null>(null);
  const [promptNode, setPromptNode] = useState<WorkflowNode | null>(null);

  async function open(name: string) {
    setPromptNode(null);
    if (!ipc) return;
    try {
      setDetail(await ipc.workflowsShow(name));
    } catch {
      setDetail(null);
    }
  }

  useEffect(() => {
    if (!ipc) return;
    ipc
      .workflowsList()
      .then((wfs) => {
        setList(wfs);
        if (wfs.length > 0) void open(wfs[0].name);
      })
      .catch(() => setList([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ipc]);

  const topology = detail?.topology ?? null;
  const flowNodes: Node[] = topology
    ? layoutTopology(topology).map((n) => ({
        id: n.id,
        position: { x: n.x, y: n.y },
        data: { label: nodeLabel(n.id) },
        ...(n.id === "__start__" ? { type: "input" as const } : {}),
        ...(n.id === "__end__" ? { type: "output" as const } : {}),
        ...(n.prompts.length === 0 && !n.id.startsWith("__")
          ? { style: { opacity: 0.7 } }
          : {}),
      }))
    : [];
  const flowEdges: Edge[] = topology
    ? topology.edges.map((e) => ({
        id: `${e.source}->${e.target}`,
        source: e.source,
        target: e.target,
        ...(e.conditional ? { style: { strokeDasharray: "6 3" } } : {}),
      }))
    : [];

  return (
    <div>
      <h1>Workflows</h1>
      <p className="page-desc">
        Registered decision pipelines. Select a workflow to see its graph; click
        an agent to edit its prompts.
      </p>
      {list.length === 0 && (
        <EmptyState
          title="No workflows registered"
          description="Workflows are defined in the platform registry. None are available in this workspace yet."
          icon={<EmptyStateIcon name="workflows" />}
        />
      )}
      <div className="master-detail">
        {list.length > 0 && (
          <div className="master-detail__list" style={{ flexBasis: 280 }}>
            {list.map((w) => (
              <div
                className={`list-item${detail?.name === w.name ? " is-selected" : ""}`}
                key={w.name}
                onClick={() => open(w.name)}
              >
                <div>
                  <strong>{w.title}</strong>{" "}
                  <span className="muted">({w.name})</span>
                </div>
                <div className="muted">{w.description}</div>
              </div>
            ))}
          </div>
        )}
        {detail && (
          <div className="master-detail__detail">
            {topology ? (
              <div style={{ height: 560 }}>
                <ReactFlow
                  nodes={flowNodes}
                  edges={flowEdges}
                  onNodeClick={(_, node) => {
                    const n = topology.nodes.find((x) => x.id === node.id);
                    if (n && n.prompts.length > 0) setPromptNode(n);
                  }}
                  fitView
                  nodesDraggable={false}
                  nodesConnectable={false}
                >
                  <Background />
                </ReactFlow>
              </div>
            ) : (
              <EmptyState
                title="No graph available"
                description="This workflow does not expose its structure."
                icon={<EmptyStateIcon name="workflows" />}
              />
            )}
          </div>
        )}
      </div>
      <NodePromptDrawer node={promptNode} onClose={() => setPromptNode(null)} />
    </div>
  );
}
