import { useEffect, useState } from "react";
import {
  Background,
  BackgroundVariant,
  Controls,
  ReactFlow,
  type NodeMouseHandler,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Typography, Segmented, Modal } from "antd";
import { useIpc } from "../app/IpcProvider";
import type { WorkflowDetail, WorkflowNode, WorkflowSummary } from "../ipc/types";
import { buildFlowNodes, buildFlowEdges } from "./workflowView";
import AgentNode from "./AgentNode";
import { WorkflowLegend } from "./WorkflowLegend";
import { NodePromptDrawer } from "./NodePromptDrawer";
import { EmptyState } from "../ui/EmptyState";
import { EmptyStateIcon } from "../ui/emptyStateIcons";
import { tokenVar } from "../ui/tokens";
import "./WorkflowsPanel.css";

const nodeTypes = { agent: AgentNode };

export function WorkflowsPanel() {
  const ipc = useIpc();
  const [list, setList] = useState<WorkflowSummary[]>([]);
  const [detail, setDetail] = useState<WorkflowDetail | null>(null);
  const [promptNode, setPromptNode] = useState<WorkflowNode | null>(null);
  const [dirty, setDirty] = useState(false);

  async function open(name: string) {
    setPromptNode(null);
    setDirty(false);
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
  const flowNodes = topology
    ? buildFlowNodes(topology, { selectedId: promptNode?.id ?? null }).map((n) => ({
        // initialWidth/Height is a size hint used only until React Flow's own
        // ResizeObserver measures the real DOM node — it never overrides a
        // real measurement, but it lets the node render immediately instead
        // of staying `visibility: hidden` for the first frame (or, in jsdom
        // where ResizeObserver never fires, indefinitely).
        ...n,
        initialWidth: 190,
        initialHeight: 64,
      }))
    : [];
  const flowEdges = topology ? buildFlowEdges(topology) : [];

  // Guarded node open: if the drawer has unsaved edits, confirm before switching.
  // `after` runs once the guard is satisfied — immediately if not dirty, or from
  // the confirm dialog's onOk if the user chooses to discard.
  function requestNode(next: WorkflowNode | null, after?: () => void) {
    if (dirty && next?.id !== promptNode?.id) {
      Modal.confirm({
        title: "Discard unsaved prompt edits?",
        content: "You have edits in the open prompt editor that haven't been saved as a new version.",
        okText: "Discard",
        cancelText: "Keep editing",
        onOk: () => {
          setDirty(false);
          setPromptNode(next);
          after?.();
        },
      });
      return;
    }
    setPromptNode(next);
    after?.();
  }

  const onNodeClick: NodeMouseHandler = (_, node) => {
    const n = topology?.nodes.find((x) => x.id === node.id);
    if (n && n.prompts.length > 0) requestNode(n);
  };

  return (
    <div className="wf-panel">
      <div className="wf-panel__head">
        <div>
          <Typography.Title level={2} style={{ margin: 0 }}>Workflows</Typography.Title>
          {detail?.title && (
            <Typography.Text strong style={{ display: "block", margin: "4px 0 0" }}>
              {detail.title}
            </Typography.Text>
          )}
          <Typography.Paragraph type="secondary" style={{ maxWidth: "66ch", margin: "4px 0 0" }}>
            {detail?.description ??
              "Registered decision pipelines. Select a workflow to inspect its reasoning graph; click an agent to edit the prompts that steer it."}
          </Typography.Paragraph>
        </div>
        {list.length > 1 && (
          <Segmented
            className="wf-panel__switcher"
            value={detail?.name}
            onChange={(v) => requestNode(null, () => void open(String(v)))}
            options={list.map((w) => ({ label: w.title, value: w.name }))}
          />
        )}
      </div>

      {list.length === 0 && (
        <EmptyState
          title="No workflows registered"
          description="Workflows are defined in the platform registry. None are available in this workspace yet."
          icon={<EmptyStateIcon name="workflows" />}
        />
      )}

      {detail && (
        topology ? (
          <div className="wf-panel__canvas">
            <ReactFlow
              nodes={flowNodes}
              edges={flowEdges}
              nodeTypes={nodeTypes}
              onNodeClick={onNodeClick}
              fitView
              fitViewOptions={{ padding: 0.2 }}
              nodesDraggable={false}
              nodesConnectable={false}
              elementsSelectable
              proOptions={{ hideAttribution: true }}
            >
              <Background variant={BackgroundVariant.Dots} gap={20} size={1} color={tokenVar("--border-subtle")} />
              <Controls showInteractive={false} />
            </ReactFlow>
            <div className="wf-panel__legend"><WorkflowLegend /></div>
          </div>
        ) : (
          <EmptyState
            title="No graph available"
            description="This workflow does not expose its structure."
            icon={<EmptyStateIcon name="workflows" />}
          />
        )
      )}

      <NodePromptDrawer node={promptNode} onClose={() => requestNode(null)} onDirtyChange={setDirty} />
    </div>
  );
}
