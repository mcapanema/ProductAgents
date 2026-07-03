import { describe, it, expect } from "vitest";
import { layoutTopology, nodeLabel, nodeRanks, buildFlowNodes, buildFlowEdges } from "./workflowView";
import type { WorkflowTopology } from "../ipc/types";

const topo: WorkflowTopology = {
  nodes: [
    { id: "__start__", prompts: [] },
    { id: "customer_research", prompts: ["customer_research"] },
    { id: "technical", prompts: ["technical"] },
    { id: "debate", prompts: ["debate"] },
    { id: "strategist", prompts: ["strategist"] },
    { id: "judge", prompts: ["judge"] },
    { id: "__end__", prompts: [] },
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
      nodes: [{ id: "orphan", prompts: [] }],
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
    { id: "__start__", prompts: [] },
    { id: "customer_research", prompts: ["customer_research"] },
    { id: "recall", prompts: [] },
    { id: "strategist", prompts: ["strategist"] },
    { id: "__end__", prompts: [] },
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
    expect(byId.customer_research.data.status).toBe("done");
    expect(byId.strategist.data.status).toBe("idle"); // default
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
});
