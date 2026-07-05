import { useCallback, useEffect, useRef, useState } from "react";
import {
  applyNodeChanges,
  Background,
  BackgroundVariant,
  Controls,
  ReactFlow,
  type Edge,
  type Node,
  type NodeChange,
  type OnSelectionChangeFunc,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Typography, Modal } from "antd";
import { useIpc } from "../app/IpcProvider";
import type { WorkflowDetail, WorkflowNode, WorkflowSummary } from "../ipc/types";
import {
  buildFlowNodes,
  buildFlowEdges,
  withSelection,
  withCachedPositions,
  cachePosition,
  type PositionCache,
} from "./workflowView";
import AgentNode, { type AgentNodeData } from "./AgentNode";
import { WorkflowLegend } from "./WorkflowLegend";
import { WorkflowSelect } from "./WorkflowSelect";
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

// Dragged positions, keyed by workflow name then node id. Module-level (not
// component state) on purpose: the app's shell conditionally renders
// `{view === "workflows" && <WorkflowsPanel />}`, so navigating to another
// sidebar panel and back fully unmounts/remounts this component — plain
// useState would lose every drag. This survives that; it resets on a full
// page reload, which is an acceptable session-only scope (ask before adding
// real backend/localStorage persistence).
const positionCache: PositionCache = new Map();

export function WorkflowsPanel() {
  const ipc = useIpc();
  const [list, setList] = useState<WorkflowSummary[]>([]);
  const [detail, setDetail] = useState<WorkflowDetail | null>(null);
  const [promptNode, setPromptNode] = useState<WorkflowNode | null>(null);
  const [dirty, setDirty] = useState(false);
  const [flowNodes, setFlowNodes] = useState<Node<AgentNodeData>[]>([]);
  const [flowEdges, setFlowEdges] = useState<Edge[]>([]);

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
  // changes — first load, a workflow switch, or this component remounting
  // (e.g. after navigating to another sidebar panel and back). A different
  // graph gets a fresh computed layout; the *same* graph gets any positions
  // the user previously dragged, restored from positionCache.
  //
  // Nodes and edges are set together, in this one effect, on purpose: edges
  // used to be recomputed inline on every render directly from `topology`,
  // while nodes only updated one render later via this effect. That gap
  // let React Flow briefly (or, under some interleavings, indefinitely) see
  // edges pointing at node ids that didn't exist yet in `flowNodes`, which
  // it silently drops. Keeping both in the same state update removes any
  // render where they can disagree.
  useEffect(() => {
    if (!topology || !detail) {
      setFlowNodes([]);
      setFlowEdges([]);
      return;
    }
    const built = withSizeHint(buildFlowNodes(topology, { selectedId: promptNode?.id ?? null }));
    setFlowNodes(withCachedPositions(built, positionCache, detail.name));
    setFlowEdges(buildFlowEdges(topology));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topology]);

  // Patch which node is selected onto the *existing* node list — e.g. after a
  // drag — without resetting anyone's position back to the computed layout.
  useEffect(() => {
    setFlowNodes((nodes) => withSelection(nodes, promptNode?.id ?? null));
  }, [promptNode?.id]);

  const onNodesChange = useCallback(
    (changes: NodeChange<Node<AgentNodeData>>[]) => {
      setFlowNodes((nodes) => applyNodeChanges(changes, nodes));
      if (!detail) return;
      for (const change of changes) {
        if (change.type === "position" && change.position) {
          cachePosition(positionCache, detail.name, change.id, change.position);
        }
      }
    },
    [detail],
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

  // React Flow re-invokes onSelectionChange on every parent render (its
  // internal listener effect depends on the callback's own identity, not just
  // on whether the selection actually changed) — so a non-memoized callback
  // here would keep firing with the *previous* selection on every unrelated
  // state update, e.g. re-opening a node right after closing it. Keep this
  // callback's identity permanently stable (empty deps) and reach for the
  // latest topology/requestNode via refs instead of closing over them.
  const topologyRef = useRef(topology);
  topologyRef.current = topology;
  const requestNodeRef = useRef(requestNode);
  requestNodeRef.current = requestNode;

  // Single source of truth for "which node opens the drawer": React Flow's own
  // selection state, driven by either a mouse click or keyboard Enter/Space on
  // a focused node — both funnel through here since `onNodesChange` is wired.
  const onSelectionChange: OnSelectionChangeFunc = useCallback(({ nodes: selected }) => {
    if (selected.length !== 1) return;
    const n = topologyRef.current?.nodes.find((x) => x.id === selected[0].id);
    if (n && n.prompts.length > 0) requestNodeRef.current(n);
  }, []);

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
        {list.length > 0 && (
          <WorkflowSelect
            workflows={list}
            value={detail?.name}
            onChange={(name) => requestNode(null, () => void open(name))}
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
              <Controls showInteractive={false} position="bottom-right" />
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
