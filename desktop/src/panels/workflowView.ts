import type { Node, Edge } from "@xyflow/react";
import type { WorkflowNode, WorkflowTopology, NodeStatus } from "../ipc/types";
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
  return layoutTopology(topology).map((n) => ({
    id: n.id,
    type: "agent",
    position: { x: n.x, y: n.y },
    data: {
      id: n.id,
      kind: nodeKind(n.id),
      status: statuses[n.id] ?? "idle",
      editable: n.prompts.length > 0,
      selected: opts.selectedId === n.id,
    },
  }));
}

/**
 * Patch which node is "selected" (drives the open-drawer ring) onto an
 * existing node list without touching position — used after a drag, where
 * `buildFlowNodes` would otherwise reset every node back to its computed
 * layout position.
 */
export function withSelection(nodes: Node<AgentNodeData>[], selectedId: string | null): Node<AgentNodeData>[] {
  return nodes.map((n) =>
    n.data.selected === (n.id === selectedId) ? n : { ...n, data: { ...n.data, selected: n.id === selectedId } },
  );
}

export function buildFlowEdges(topology: WorkflowTopology): Edge[] {
  return topology.edges.map((e) => ({
    id: `${e.source}->${e.target}`,
    source: e.source,
    target: e.target,
    style: {
      stroke: tokenVar("--ai-edge"),
      strokeWidth: 1.5,
      ...(e.conditional ? { strokeDasharray: "6 4" } : {}),
    },
  }));
}
