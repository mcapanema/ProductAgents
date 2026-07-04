import type { Node, Edge } from "@xyflow/react";
import type { WorkflowNode, WorkflowTopology, WorkflowDefinitionDTO, NodeStatus } from "../ipc/types";
import { nodeKind } from "./workflowNodeKinds";
import type { AgentNodeData } from "./AgentNode";
import { tokenVar } from "../ui/tokens";

export interface PositionedNode extends WorkflowNode {
  x: number;
  y: number;
}

const X_STEP = 190;
const Y_STEP = 110;

/** "customer_research" → "Customer Research", "__start__" → "Start". */
export function nodeLabel(id: string): string {
  return id
    .replace(/_/g, " ")
    .trim()
    .split(/\s+/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/**
 * Rank each node by its longest path from __start__, skipping edges that
 * close a cycle (the judge → strategist retry loop). Nodes unreachable from
 * __start__ get rank 0. ponytail: plain DFS re-walks shared paths —
 * exponential in theory, instant at pipeline sizes; memoize if a workflow
 * ever grows past a few dozen nodes.
 */
export function nodeRanks(topology: WorkflowTopology): Map<string, number> {
  const out = new Map<string, string[]>();
  for (const e of topology.edges) {
    out.set(e.source, [...(out.get(e.source) ?? []), e.target]);
  }
  const rank = new Map<string, number>();
  const stack = new Set<string>();
  const visit = (id: string, depth: number) => {
    if (stack.has(id)) return; // cycle edge — skip
    rank.set(id, Math.max(rank.get(id) ?? 0, depth));
    stack.add(id);
    for (const next of out.get(id) ?? []) visit(next, depth + 1);
    stack.delete(id);
  };
  visit("__start__", 0);
  for (const n of topology.nodes) if (!rank.has(n.id)) rank.set(n.id, 0);
  return rank;
}

/** Top-down layered layout: row = rank, columns centered within the widest rank. */
export function layoutTopology(topology: WorkflowTopology): PositionedNode[] {
  const ranks = nodeRanks(topology);
  const widths = new Map<number, number>();
  for (const n of topology.nodes) {
    const r = ranks.get(n.id) ?? 0;
    widths.set(r, (widths.get(r) ?? 0) + 1);
  }
  const widest = Math.max(1, ...widths.values());
  const placed = new Map<number, number>();
  return topology.nodes.map((n) => {
    const r = ranks.get(n.id) ?? 0;
    const col = placed.get(r) ?? 0;
    placed.set(r, col + 1);
    const offset = ((widest - (widths.get(r) ?? 1)) * X_STEP) / 2;
    return { ...n, x: offset + col * X_STEP, y: r * Y_STEP };
  });
}

export function buildFlowNodes(
  topology: WorkflowTopology,
  opts: { selectedId?: string | null; statuses?: Record<string, NodeStatus> },
): Node<AgentNodeData>[] {
  const statuses = opts.statuses ?? {};
  return layoutTopology(topology).map((n) => {
    const selected = opts.selectedId === n.id;
    return {
      id: n.id,
      type: "agent",
      position: { x: n.x, y: n.y },
      // `selected` (top-level) is React Flow's own selection flag; keep it in
      // sync with `data.selected` (our ring styling) from the start — see
      // withSelection()'s comment for why the two must never drift apart.
      selected,
      data: {
        id: n.id,
        // Look up the visual category by the backend *kind* (e.g. "market"),
        // not the node's own id — a duplicated analyst instance has an id
        // like "market#2" that nodeKind() wouldn't otherwise resolve.
        kind: nodeKind(n.kind || n.id),
        backendKind: n.kind || n.id,
        config: n.config,
        status: statuses[n.id] ?? "idle",
        editable: n.prompts.length > 0,
        selected,
      },
    };
  });
}

/**
 * Patch which node is "selected" (drives the open-drawer ring) onto an
 * existing node list without touching position — used after a drag, where
 * `buildFlowNodes` would otherwise reset every node back to its computed
 * layout position.
 *
 * Sets both `data.selected` (our own ring styling) AND the node's top-level
 * `selected` (React Flow's own internal selection flag). Skipping the latter
 * left RF believing a closed node was still selected, so re-syncing the
 * `nodes` prop kept re-deriving the same "selected" node and reopening its
 * drawer — closing never stuck.
 */
export function withSelection(nodes: Node<AgentNodeData>[], selectedId: string | null): Node<AgentNodeData>[] {
  return nodes.map((n) => {
    const selected = n.id === selectedId;
    return n.data.selected === selected && n.selected === selected
      ? n
      : { ...n, selected, data: { ...n.data, selected } };
  });
}

export type PositionCache = Map<string, Record<string, { x: number; y: number }>>;

/** Restore any previously-dragged positions (from cachePosition) for a workflow. */
export function withCachedPositions(
  nodes: Node<AgentNodeData>[],
  cache: PositionCache,
  workflowName: string,
): Node<AgentNodeData>[] {
  const cached = cache.get(workflowName);
  if (!cached) return nodes;
  return nodes.map((n) => (cached[n.id] ? { ...n, position: cached[n.id] } : n));
}

/** Record a node's dragged position, scoped to one workflow so switching workflows doesn't leak positions. */
export function cachePosition(
  cache: PositionCache,
  workflowName: string,
  nodeId: string,
  position: { x: number; y: number },
): void {
  const forWorkflow = cache.get(workflowName) ?? {};
  forWorkflow[nodeId] = position;
  cache.set(workflowName, forWorkflow);
}

export function buildFlowEdges(topology: WorkflowTopology): Edge[] {
  return topology.edges.map((e) => ({
    id: `${e.source}->${e.target}`,
    source: e.source,
    target: e.target,
    data: { conditional: e.conditional },
    style: {
      stroke: tokenVar("--ai-edge"),
      strokeWidth: 1.5,
      ...(e.conditional ? { strokeDasharray: "6 4" } : {}),
    },
  }));
}

/**
 * Convert React Flow's editable state back into a `WorkflowDefinitionDTO` for
 * `ipc.workflowsSave`. `__start__`/`__end__` are terminal markers rendered on
 * the canvas, never real node instances — excluded from both `nodes` and
 * `layout` (their edges pass through unfiltered, as before). `human_approval`
 * is a builder-managed preview node `definition_topology` synthesizes
 * whenever HITL is on (always, for the desktop GUI) — not user-placeable, so
 * it's excluded from `nodes`/`layout` too, and any edge touching it
 * (`governance -> human_approval`, `human_approval -> __end__`) is dropped —
 * an edge to a node that isn't being saved would otherwise reach the backend
 * referencing an unknown node. Each node's backend `kind` (e.g. "market")
 * comes from `data.backendKind`, set by `buildFlowNodes`/the palette's
 * add-node handler — falling back to the node id covers a hand-built node
 * missing it.
 */
export function flowToDefinition(
  nodes: Node<AgentNodeData>[],
  edges: Edge[],
  base: { name: string; title: string; description: string; builtin: boolean },
): WorkflowDefinitionDTO {
  const real = nodes.filter((n) => n.id !== "__start__" && n.id !== "__end__" && n.id !== "human_approval");
  const realEdges = edges.filter((e) => e.source !== "human_approval" && e.target !== "human_approval");
  return {
    ...base,
    nodes: real.map((n) => ({
      id: n.id,
      kind: (n.data.backendKind as string | undefined) ?? n.id,
      config: (n.data.config as Record<string, unknown> | undefined) ?? {},
    })),
    edges: realEdges.map((e) => ({
      source: e.source,
      target: e.target,
      conditional: Boolean((e.data as { conditional?: boolean } | undefined)?.conditional),
    })),
    layout: Object.fromEntries(
      real.map((n) => [n.id, [n.position.x, n.position.y] as [number, number]]),
    ),
  };
}
