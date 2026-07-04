import { describe, it, expect } from "vitest";
import {
  layoutTopology,
  nodeLabel,
  nodeRanks,
  buildFlowNodes,
  buildFlowEdges,
  flowToDefinition,
  withSelection,
  withCachedPositions,
  cachePosition,
  type PositionCache,
} from "./workflowView";
import type { WorkflowTopology } from "../ipc/types";

const topo: WorkflowTopology = {
  nodes: [
    { id: "__start__", prompts: [], kind: "__start__", config: {} },
    { id: "customer_research", prompts: ["customer_research"], kind: "customer_research", config: {} },
    { id: "technical", prompts: ["technical"], kind: "technical", config: {} },
    { id: "debate", prompts: ["debate"], kind: "debate", config: {} },
    { id: "strategist", prompts: ["strategist"], kind: "strategist", config: {} },
    { id: "judge", prompts: ["judge"], kind: "judge", config: {} },
    { id: "__end__", prompts: [], kind: "__end__", config: {} },
  ],
  edges: [
    { source: "__start__", target: "customer_research", conditional: false },
    { source: "__start__", target: "technical", conditional: false },
    { source: "customer_research", target: "debate", conditional: false },
    { source: "technical", target: "debate", conditional: false },
    { source: "debate", target: "strategist", conditional: false },
    { source: "strategist", target: "judge", conditional: true },
    { source: "judge", target: "strategist", conditional: true }, // retry cycle
    { source: "judge", target: "__end__", conditional: true },
    { source: "strategist", target: "__end__", conditional: true },
  ],
};

describe("nodeLabel", () => {
  it("humanizes snake_case ids", () => {
    expect(nodeLabel("customer_research")).toBe("Customer Research");
  });
  it("strips dunder markers", () => {
    expect(nodeLabel("__start__")).toBe("Start");
    expect(nodeLabel("__end__")).toBe("End");
  });
});

describe("nodeRanks", () => {
  it("ranks by longest path from __start__ and survives the retry cycle", () => {
    const ranks = nodeRanks(topo);
    expect(ranks.get("__start__")).toBe(0);
    expect(ranks.get("customer_research")).toBe(1);
    expect(ranks.get("debate")).toBe(2);
    expect(ranks.get("strategist")).toBe(3);
    expect(ranks.get("judge")).toBe(4);
    // longest path wins: via judge, not the shorter strategist → __end__ edge
    expect(ranks.get("__end__")).toBe(5);
  });

  it("gives unreachable nodes rank 0 instead of dropping them", () => {
    const ranks = nodeRanks({
      nodes: [{ id: "orphan", prompts: [], kind: "orphan", config: {} }],
      edges: [],
    });
    expect(ranks.get("orphan")).toBe(0);
  });
});

describe("layoutTopology", () => {
  it("stacks ranks top-down and spreads same-rank siblings horizontally", () => {
    const byId = Object.fromEntries(
      layoutTopology(topo).map((n) => [n.id, n]),
    );
    expect(byId.customer_research.y).toBe(byId.technical.y);
    expect(byId.customer_research.x).not.toBe(byId.technical.x);
    expect(byId.debate.y).toBeGreaterThan(byId.customer_research.y);
    expect(byId.__end__.y).toBeGreaterThan(byId.judge.y);
  });
});

const topoSmall: WorkflowTopology = {
  nodes: [
    { id: "__start__", prompts: [], kind: "__start__", config: {} },
    { id: "customer_research", prompts: ["customer_research"], kind: "customer_research", config: {} },
    { id: "recall", prompts: [], kind: "recall", config: {} },
    { id: "strategist", prompts: ["strategist"], kind: "strategist", config: {} },
    { id: "__end__", prompts: [], kind: "__end__", config: {} },
  ],
  edges: [
    { source: "__start__", target: "customer_research", conditional: false },
    { source: "customer_research", target: "strategist", conditional: false },
    { source: "strategist", target: "__end__", conditional: true },
  ],
};

describe("buildFlowNodes", () => {
  it("types every node as 'agent' and carries kind + editability", () => {
    const nodes = buildFlowNodes(topoSmall, {});
    const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
    expect(nodes.every((n) => n.type === "agent")).toBe(true);
    expect(byId.customer_research.data.kind).toBe("analyst-customer");
    expect(byId.customer_research.data.editable).toBe(true); // has prompts
    expect(byId.recall.data.editable).toBe(false); // no prompts
    expect(byId.__start__.data.kind).toBe("terminal");
  });

  it("marks the selected node and applies statuses", () => {
    const nodes = buildFlowNodes(topoSmall, {
      selectedId: "strategist",
      statuses: { customer_research: "done" },
    });
    const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
    expect(byId.strategist.data.selected).toBe(true);
    expect(byId.strategist.selected).toBe(true); // React Flow's own selection flag, kept in sync
    expect(byId.customer_research.data.status).toBe("done");
    expect(byId.strategist.data.status).toBe("idle"); // default
  });
});

describe("withSelection", () => {
  it("marks only the given node id as selected, leaving other fields (like position) untouched", () => {
    const nodes = buildFlowNodes(topoSmall, { selectedId: "customer_research" });
    const dragged = nodes.map((n) => (n.id === "strategist" ? { ...n, position: { x: 999, y: 999 } } : n));
    const patched = withSelection(dragged, "strategist");
    const byId = Object.fromEntries(patched.map((n) => [n.id, n]));
    expect(byId.strategist.data.selected).toBe(true);
    expect(byId.customer_research.data.selected).toBe(false); // previous selection cleared
    expect(byId.strategist.position).toEqual({ x: 999, y: 999 }); // the drag survives
  });

  it("keeps React Flow's own top-level `selected` flag in sync with `data.selected`", () => {
    // Regression: only patching data.selected left React Flow believing a
    // closed node was still selected, which re-derived the same selection
    // and reopened its drawer — closing never stuck.
    const nodes = buildFlowNodes(topoSmall, { selectedId: "strategist" });
    const closed = withSelection(nodes, null);
    expect(closed.every((n) => n.selected === false)).toBe(true);
    const reselected = withSelection(closed, "customer_research");
    const byId = Object.fromEntries(reselected.map((n) => [n.id, n]));
    expect(byId.customer_research.selected).toBe(true);
    expect(byId.strategist.selected).toBe(false);
  });

  it("returns a new array reference only for nodes whose selected flag actually changed", () => {
    const nodes = buildFlowNodes(topoSmall, { selectedId: "strategist" });
    const patched = withSelection(nodes, "strategist");
    const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
    const patchedById = Object.fromEntries(patched.map((n) => [n.id, n]));
    expect(patchedById.strategist).toBe(byId.strategist); // unchanged: same object
    expect(patchedById.customer_research).toBe(byId.customer_research); // unchanged: same object
  });

  it("clears selection when passed null", () => {
    const nodes = buildFlowNodes(topoSmall, { selectedId: "strategist" });
    const patched = withSelection(nodes, null);
    expect(patched.every((n) => n.data.selected === false && n.selected === false)).toBe(true);
  });
});

describe("cachePosition / withCachedPositions", () => {
  it("restores a cached position onto a matching node, leaving others at their computed layout", () => {
    const cache: PositionCache = new Map();
    cachePosition(cache, "wf-a", "strategist", { x: 999, y: 999 });
    const nodes = buildFlowNodes(topoSmall, {});
    const restored = withCachedPositions(nodes, cache, "wf-a");
    const byId = Object.fromEntries(restored.map((n) => [n.id, n]));
    expect(byId.strategist.position).toEqual({ x: 999, y: 999 });
    expect(byId.customer_research.position).toEqual(
      buildFlowNodes(topoSmall, {}).find((n) => n.id === "customer_research")!.position,
    );
  });

  it("scopes cached positions per workflow — one workflow's drag never leaks into another's", () => {
    const cache: PositionCache = new Map();
    cachePosition(cache, "wf-a", "strategist", { x: 111, y: 111 });
    const nodes = buildFlowNodes(topoSmall, {});
    const restoredForOtherWorkflow = withCachedPositions(nodes, cache, "wf-b");
    expect(restoredForOtherWorkflow).toBe(nodes); // no cache entry for wf-b — untouched
  });

  it("returns the input array unchanged when nothing is cached for that workflow yet", () => {
    const cache: PositionCache = new Map();
    const nodes = buildFlowNodes(topoSmall, {});
    expect(withCachedPositions(nodes, cache, "wf-a")).toBe(nodes);
  });

  it("later cachePosition calls for the same node overwrite the earlier one", () => {
    const cache: PositionCache = new Map();
    cachePosition(cache, "wf-a", "strategist", { x: 1, y: 1 });
    cachePosition(cache, "wf-a", "strategist", { x: 2, y: 2 });
    const nodes = buildFlowNodes(topoSmall, {});
    const restored = withCachedPositions(nodes, cache, "wf-a");
    expect(restored.find((n) => n.id === "strategist")!.position).toEqual({ x: 2, y: 2 });
  });
});

describe("buildFlowEdges", () => {
  it("dashes conditional edges and colors edges from the ai-edge token", () => {
    const edges = buildFlowEdges(topoSmall);
    const cond = edges.find((e) => e.id === "strategist->__end__")!;
    expect(cond.style?.strokeDasharray).toBeTruthy();
    expect(String(cond.style?.stroke)).toContain("var(--ai-edge");
    const plain = edges.find((e) => e.id === "__start__->customer_research")!;
    expect(plain.style?.strokeDasharray).toBeFalsy();
  });

  it("carries conditional in data and a stable id", () => {
    const edges = buildFlowEdges({
      nodes: [],
      edges: [{ source: "strategist", target: "judge", conditional: true }],
    });
    expect(edges[0].id).toBe("strategist->judge");
    expect((edges[0].data as { conditional?: boolean }).conditional).toBe(true);
  });
});

describe("flowToDefinition", () => {
  it("captures positions as layout and preserves kind/config", () => {
    const defn = flowToDefinition(
      [
        {
          id: "market",
          type: "agent",
          position: { x: 5, y: 9 },
          data: { id: "market", kind: "analyst-market", backendKind: "market", config: {}, status: "idle", editable: true, selected: false },
        },
      ],
      [],
      { name: "d", title: "D", description: "", builtin: false },
    );
    expect(defn.nodes[0]).toMatchObject({ id: "market", kind: "market" });
    expect(defn.layout.market).toEqual([5, 9]);
  });

  it("excludes the __start__/__end__ terminal markers from nodes and layout", () => {
    const defn = flowToDefinition(
      [
        { id: "__start__", type: "agent", position: { x: 0, y: 0 }, data: { id: "__start__", kind: "terminal", backendKind: "__start__", config: {}, status: "idle", editable: false, selected: false } },
        { id: "strategist", type: "agent", position: { x: 5, y: 9 }, data: { id: "strategist", kind: "strategist", backendKind: "strategist", config: {}, status: "idle", editable: true, selected: false } },
      ],
      [{ id: "__start__->strategist", source: "__start__", target: "strategist", data: { conditional: false } }],
      { name: "d", title: "D", description: "", builtin: false },
    );
    expect(defn.nodes.map((n) => n.id)).toEqual(["strategist"]);
    expect(defn.layout).toEqual({ strategist: [5, 9] });
    expect(defn.edges).toEqual([{ source: "__start__", target: "strategist", conditional: false }]);
  });

  it("excludes the synthesized human_approval preview node, drops its synthetic edge, and restores the real end-edge", () => {
    const defn = flowToDefinition(
      [
        { id: "governance", type: "agent", position: { x: 0, y: 0 }, data: { id: "governance", kind: "governance", backendKind: "governance", config: {}, status: "idle", editable: true, selected: false } },
        { id: "human_approval", type: "agent", position: { x: 5, y: 9 }, data: { id: "human_approval", kind: "approval", backendKind: "human_approval", config: {}, status: "idle", editable: false, selected: false } },
        { id: "__end__", type: "agent", position: { x: 10, y: 18 }, data: { id: "__end__", kind: "terminal", backendKind: "__end__", config: {}, status: "idle", editable: false, selected: false } },
      ],
      [
        { id: "governance->human_approval", source: "governance", target: "human_approval", data: { conditional: false } },
        { id: "human_approval->__end__", source: "human_approval", target: "__end__", data: { conditional: false } },
      ],
      { name: "d", title: "D", description: "", builtin: false },
    );
    expect(defn.nodes.map((n) => n.id)).toEqual(["governance"]);
    expect(defn.layout).toEqual({ governance: [0, 0] });
    expect(defn.edges).toEqual([{ source: "governance", target: "__end__", conditional: false }]);
  });

  it("restores every retargeted edge when multiple nodes originally targeted __end__", () => {
    const defn = flowToDefinition(
      [
        { id: "riskA", type: "agent", position: { x: 0, y: 0 }, data: { id: "riskA", kind: "risk", backendKind: "risk", config: {}, status: "idle", editable: true, selected: false } },
        { id: "riskB", type: "agent", position: { x: 1, y: 1 }, data: { id: "riskB", kind: "risk", backendKind: "risk", config: {}, status: "idle", editable: true, selected: false } },
        { id: "human_approval", type: "agent", position: { x: 5, y: 9 }, data: { id: "human_approval", kind: "approval", backendKind: "human_approval", config: {}, status: "idle", editable: false, selected: false } },
        { id: "__end__", type: "agent", position: { x: 10, y: 18 }, data: { id: "__end__", kind: "terminal", backendKind: "__end__", config: {}, status: "idle", editable: false, selected: false } },
      ],
      [
        { id: "riskA->human_approval", source: "riskA", target: "human_approval", data: { conditional: false } },
        { id: "riskB->human_approval", source: "riskB", target: "human_approval", data: { conditional: true } },
        { id: "human_approval->__end__", source: "human_approval", target: "__end__", data: { conditional: false } },
      ],
      { name: "d", title: "D", description: "", builtin: false },
    );
    expect(defn.edges).toEqual([
      { source: "riskA", target: "__end__", conditional: false },
      { source: "riskB", target: "__end__", conditional: true },
    ]);
  });
});
