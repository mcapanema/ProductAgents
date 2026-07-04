import { useCallback, useEffect, useRef, useState } from "react";
import {
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  Background,
  BackgroundVariant,
  Controls,
  ReactFlow,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
  type OnSelectionChangeFunc,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Typography, Modal, Alert } from "antd";
import { useIpc } from "../app/IpcProvider";
import type { PaletteKind, WorkflowDetail, WorkflowNode, WorkflowSummary } from "../ipc/types";
import {
  buildFlowNodes,
  buildFlowEdges,
  flowToDefinition,
  withSelection,
  withCachedPositions,
  cachePosition,
  type PositionCache,
} from "./workflowView";
import AgentNode, { type AgentNodeData } from "./AgentNode";
import { WorkflowLegend } from "./WorkflowLegend";
import { NodePromptDrawer } from "./NodePromptDrawer";
import { WorkflowPalette, newInstanceId } from "./WorkflowPalette";
import { WorkflowToolbar } from "./WorkflowToolbar";
import { nodeKind } from "./workflowNodeKinds";
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
  const [palette, setPalette] = useState<PaletteKind[]>([]);
  const [graphDirty, setGraphDirty] = useState(false);
  const [saveState, setSaveState] = useState<"idle" | "saved" | "error">("idle");
  const [saveError, setSaveError] = useState("");
  const [crudError, setCrudError] = useState("");

  const markGraphDirty = useCallback(() => {
    setGraphDirty(true);
    setSaveState("idle");
  }, []);

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

  // Refetch the workflow list after a CRUD mutation, then re-open `reopen`
  // (or the first remaining workflow) so `detail` — and its `is_default`/
  // `builtin` flags the toolbar renders from — reflects the mutation.
  async function refreshList(reopen?: string) {
    if (!ipc) return;
    try {
      const wfs = await ipc.workflowsList();
      setList(wfs);
      if (reopen) await open(reopen);
      else if (wfs.length > 0) await open(wfs[0].name);
      else setDetail(null);
    } catch {
      setList([]);
    }
  }

  // These five reject on failure (instead of swallowing) so both the
  // toolbar's modal (which awaits them to decide whether to close) and this
  // panel's own `crudError` Alert below can surface what went wrong — e.g. a
  // duplicate name on Create — instead of failing silently.
  function failCrud(err: unknown): never {
    setCrudError(err instanceof Error ? err.message : String(err));
    throw err;
  }
  const onCreateWorkflow = useCallback(
    (name: string, title: string) => {
      if (!ipc) return Promise.reject(new Error("Not connected."));
      setCrudError("");
      return ipc.workflowsCreate(name, title).then(() => refreshList(name)).catch(failCrud);
    },
    [ipc], // eslint-disable-line react-hooks/exhaustive-deps
  );
  const onCloneWorkflow = useCallback(
    (newName: string, title: string) => {
      if (!ipc || !detail) return Promise.reject(new Error("No workflow selected."));
      setCrudError("");
      return ipc.workflowsClone(detail.name, newName, title || undefined).then(() => refreshList(newName)).catch(failCrud);
    },
    [ipc, detail], // eslint-disable-line react-hooks/exhaustive-deps
  );
  const onRenameWorkflow = useCallback(
    (newName: string) => {
      if (!ipc || !detail) return Promise.reject(new Error("No workflow selected."));
      setCrudError("");
      return ipc.workflowsRename(detail.name, newName).then(() => refreshList(newName)).catch(failCrud);
    },
    [ipc, detail], // eslint-disable-line react-hooks/exhaustive-deps
  );
  const onDeleteWorkflow = useCallback(() => {
    if (!ipc || !detail) return Promise.reject(new Error("No workflow selected."));
    setCrudError("");
    return ipc.workflowsDelete(detail.name).then(() => refreshList()).catch(failCrud);
  }, [ipc, detail]); // eslint-disable-line react-hooks/exhaustive-deps
  const onSetDefaultWorkflow = useCallback(() => {
    if (!ipc || !detail) return Promise.reject(new Error("No workflow selected."));
    setCrudError("");
    return ipc.workflowsSetDefault(detail.name).then(() => refreshList(detail.name)).catch(failCrud);
  }, [ipc, detail]); // eslint-disable-line react-hooks/exhaustive-deps

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

  useEffect(() => {
    if (!ipc) return;
    ipc.workflowsPalette().then(setPalette).catch(() => setPalette([]));
  }, [ipc]);

  const topology = detail?.topology ?? null;

  // Recompute the layout (including positions) only when the topology itself
  // changes — first load, a workflow switch, or this component remounting
  // (e.g. after navigating to another sidebar panel and back). A different
  // graph gets a fresh computed layout; the *same* graph gets any positions
  // the user previously dragged, restored from positionCache.
  useEffect(() => {
    if (!topology || !detail) {
      setFlowNodes([]);
      setFlowEdges([]);
      return;
    }
    const built = withSizeHint(buildFlowNodes(topology, { selectedId: promptNode?.id ?? null }));
    setFlowNodes(withCachedPositions(built, positionCache, detail.name));
    setFlowEdges(buildFlowEdges(topology));
    setGraphDirty(false);
    setSaveState("idle");
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
          markGraphDirty();
        }
        if (change.type === "remove") markGraphDirty();
      }
    },
    [detail, markGraphDirty],
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      setFlowEdges((es) => applyEdgeChanges(changes, es));
      if (changes.some((c) => c.type === "remove")) markGraphDirty();
    },
    [markGraphDirty],
  );

  const onConnect = useCallback(
    (c: Connection) => {
      setFlowEdges((es) => addEdge({ ...c, id: `${c.source}->${c.target}`, data: { conditional: false } }, es));
      markGraphDirty();
    },
    [markGraphDirty],
  );

  // Add a new instance of a palette kind to the canvas at a fixed drop point
  // (drag to reposition — no collision avoidance beyond newInstanceId's own
  // id-suffixing). Prompt-editability mirrors buildFlowNodes: does this kind
  // render any prompts, per the palette entry's own `prompts` list.
  const addNode = useCallback(
    (kind: string) => {
      setFlowNodes((ns) => {
        const id = newInstanceId(kind, new Set(ns.map((n) => n.id)));
        const meta = palette.find((p) => p.kind === kind);
        const node: Node<AgentNodeData> = {
          id,
          type: "agent",
          position: { x: 40, y: 40 },
          initialWidth: 190,
          initialHeight: 64,
          data: {
            id,
            kind: nodeKind(kind),
            backendKind: kind,
            config: {},
            status: "idle",
            editable: (meta?.prompts.length ?? 0) > 0,
            selected: false,
          },
        };
        return [...ns, node];
      });
      markGraphDirty();
    },
    [palette, markGraphDirty],
  );

  const save = useCallback(async () => {
    if (!ipc || !detail) return;
    try {
      await ipc.workflowsSave(
        flowToDefinition(flowNodes, flowEdges, {
          name: detail.name,
          title: detail.title,
          description: detail.description,
          builtin: detail.definition.builtin,
        }),
      );
      setGraphDirty(false);
      setSaveState("saved");
    } catch (err) {
      setSaveState("error");
      setSaveError(err instanceof Error ? err.message : String(err));
    }
  }, [ipc, detail, flowNodes, flowEdges]);

  // Guarded node open: if the drawer has unsaved prompt edits, or (when
  // `checkGraph` is set — i.e. a workflow switch, the only action that
  // actually discards canvas state) the canvas has unsaved edits, confirm
  // before proceeding. `after` runs once the guard is satisfied — immediately
  // if nothing's dirty, or from the confirm dialog's onOk if the user chooses
  // to discard.
  function requestNode(next: WorkflowNode | null, after?: () => void, checkGraph = false) {
    const promptDirty = dirty && next?.id !== promptNode?.id;
    const canvasDirty = checkGraph && graphDirty;
    if (promptDirty || canvasDirty) {
      const title = promptDirty && canvasDirty
        ? "Discard unsaved changes?"
        : canvasDirty
          ? "Discard unsaved canvas changes?"
          : "Discard unsaved prompt edits?";
      const content = promptDirty && canvasDirty
        ? "You have unsaved prompt edits and unsaved canvas changes (added nodes, edges, or moved positions). Switching workflows will discard both."
        : canvasDirty
          ? "You have unsaved canvas changes (added nodes, edges, or moved positions) that will be lost if you switch workflows."
          : "You have edits in the open prompt editor that haven't been saved as a new version.";
      Modal.confirm({
        title,
        content,
        okText: "Discard",
        cancelText: "Keep editing",
        onOk: () => {
          setDirty(false);
          if (canvasDirty) setGraphDirty(false);
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
      </div>

      <WorkflowToolbar
        workflows={list}
        current={detail ? { ...detail, builtin: detail.definition.builtin } : null}
        dirty={graphDirty && !!ipc}
        onSelect={(name) => requestNode(null, () => void open(name), true)}
        onCreate={onCreateWorkflow}
        onClone={onCloneWorkflow}
        onRename={onRenameWorkflow}
        onDelete={onDeleteWorkflow}
        onSetDefault={onSetDefaultWorkflow}
        onSave={() => void save()}
      />
      {saveState === "saved" && (
        <Alert type="success" showIcon message="Workflow saved." style={{ padding: "2px 8px" }} />
      )}
      {saveState === "error" && (
        <Alert type="error" showIcon message={saveError || "Couldn't save — try again."} style={{ padding: "2px 8px" }} />
      )}
      {crudError && (
        <Alert
          type="error"
          showIcon
          closable
          onClose={() => setCrudError("")}
          message={crudError}
          style={{ padding: "2px 8px" }}
        />
      )}

      {list.length === 0 && (
        <EmptyState
          title="No workflows registered"
          description="Workflows are defined in the platform registry. None are available in this workspace yet."
          icon={<EmptyStateIcon name="workflows" />}
        />
      )}

      {detail && (
        topology ? (
          <>
            <div className="wf-panel__editor">
              <WorkflowPalette palette={palette} onAdd={addNode} />
              <div className="wf-panel__canvas">
                <ReactFlow
                  nodes={flowNodes}
                  edges={flowEdges}
                  nodeTypes={nodeTypes}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesChange}
                  onConnect={onConnect}
                  onSelectionChange={onSelectionChange}
                  fitView
                  fitViewOptions={{ padding: 0.2 }}
                  nodesConnectable
                  elementsSelectable
                  selectNodesOnDrag={false}
                  deleteKeyCode={["Backspace", "Delete"]}
                  proOptions={{ hideAttribution: true }}
                >
                  <Background variant={BackgroundVariant.Dots} gap={20} size={1} color={tokenVar("--border-subtle")} />
                  <Controls showInteractive={false} />
                </ReactFlow>
                <div className="wf-panel__legend"><WorkflowLegend /></div>
              </div>
            </div>
          </>
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
