import { useCallback, useEffect, useState } from "react";
import {
  applyNodeChanges,
  Background,
  BackgroundVariant,
  Controls,
  ReactFlow,
  type Node,
  type NodeChange,
  type OnSelectionChangeFunc,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Typography, Segmented, Modal } from "antd";
import { useIpc } from "../app/IpcProvider";
import type { WorkflowDetail, WorkflowNode, WorkflowSummary } from "../ipc/types";
import { buildFlowNodes, buildFlowEdges, withSelection } from "./workflowView";
import AgentNode, { type AgentNodeData } from "./AgentNode";
import { WorkflowLegend } from "./WorkflowLegend";
import { NodePromptDrawer } from "./NodePromptDrawer";
import { EmptyState } from "../ui/EmptyState";
import { EmptyStateIcon } from "../ui/emptyStateIcons";
import { tokenVar } from "../ui/tokens";
import "./WorkflowsPanel.css";

const nodeTypes = { agent: AgentNode };

// initialWidth/Height is a size hint used only until React Flow's own
// ResizeObserver measures the real DOM node — it never overrides a real
// measurement, but it lets the node render immediately instead of staying
// `visibility: hidden` for the first frame (or, in jsdom where
// ResizeObserver never fires, indefinitely).
function withSizeHint(nodes: Node<AgentNodeData>[]): Node<AgentNodeData>[] {
  return nodes.map((n) => ({ ...n, initialWidth: 190, initialHeight: 64 }));
}

export function WorkflowsPanel() {
  const ipc = useIpc();
  const [list, setList] = useState<WorkflowSummary[]>([]);
  const [detail, setDetail] = useState<WorkflowDetail | null>(null);
  const [promptNode, setPromptNode] = useState<WorkflowNode | null>(null);
  const [dirty, setDirty] = useState(false);
  const [flowNodes, setFlowNodes] = useState<Node<AgentNodeData>[]>([]);

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

  // Recompute the layout (including positions) only when the topology itself
  // changes — first load or a workflow switch. A different graph has a
  // different natural layout, so dragged positions intentionally don't
  // survive a workflow switch.
  useEffect(() => {
    setFlowNodes(topology ? withSizeHint(buildFlowNodes(topology, { selectedId: promptNode?.id ?? null })) : []);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topology]);

  // Patch which node is selected onto the *existing* node list — e.g. after a
  // drag — without resetting anyone's position back to the computed layout.
  useEffect(() => {
    setFlowNodes((nodes) => withSelection(nodes, promptNode?.id ?? null));
  }, [promptNode?.id]);

  const flowEdges = topology ? buildFlowEdges(topology) : [];

  const onNodesChange = useCallback(
    (changes: NodeChange<Node<AgentNodeData>>[]) => setFlowNodes((nodes) => applyNodeChanges(changes, nodes)),
    [],
  );

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

  // Single source of truth for "which node opens the drawer": React Flow's own
  // selection state, driven by either a mouse click or keyboard Enter/Space on
  // a focused node — both funnel through here since `onNodesChange` is wired.
  const onSelectionChange: OnSelectionChangeFunc = ({ nodes: selected }) => {
    if (selected.length !== 1) return;
    const n = topology?.nodes.find((x) => x.id === selected[0].id);
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
              onNodesChange={onNodesChange}
              onSelectionChange={onSelectionChange}
              fitView
              fitViewOptions={{ padding: 0.2 }}
              nodesConnectable={false}
              elementsSelectable
              selectNodesOnDrag={false}
              deleteKeyCode={null}
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
