import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { WorkflowsPanel } from "./WorkflowsPanel";
import { IpcProvider } from "../app/IpcProvider";
import type { IpcClient } from "../ipc/client";
import type { WorkflowDetail, WorkflowSummary } from "../ipc/types";

const summary: WorkflowSummary = {
  name: "evaluate_initiative",
  title: "Evaluate Initiative",
  description: "Advisory pipeline: evidence → analysts → debate → strategist.",
};

const detail: WorkflowDetail = {
  ...summary,
  topology: {
    nodes: [
      { id: "__start__", prompts: [] },
      { id: "strategist", prompts: ["strategist"] },
      { id: "__end__", prompts: [] },
    ],
    edges: [
      { source: "__start__", target: "strategist", conditional: false },
      { source: "strategist", target: "__end__", conditional: true },
    ],
  },
};

export function fake(overrides: Record<string, unknown> = {}): IpcClient {
  return {
    workflowsList: async () => [summary],
    workflowsShow: async () => detail,
    promptsList: async () => [{ name: "strategist", versions: [0], active: 0 }],
    promptsShow: async () => ({ name: "strategist", version: 0, text: "Decide." }),
    promptsSave: async () => ({ name: "strategist", versions: [0, 1], active: 1 }),
    ...overrides,
  } as unknown as IpcClient;
}

export function renderPanel(client: IpcClient) {
  render(
    <IpcProvider client={client}>
      <WorkflowsPanel />
    </IpcProvider>,
  );
}

describe("WorkflowsPanel", () => {
  it("lists workflows and renders the selected workflow's graph", async () => {
    renderPanel(fake());
    expect(await screen.findByText("Evaluate Initiative")).toBeInTheDocument();
    expect(await screen.findByText("Strategist")).toBeInTheDocument();
    expect(screen.getByText("Start")).toBeInTheDocument();
    expect(screen.getByText("End")).toBeInTheDocument();
  });

  it("shows an empty state when there are no workflows", async () => {
    renderPanel(fake({ workflowsList: async () => [] }));
    expect(await screen.findByText(/no workflows/i)).toBeInTheDocument();
  });

  it("shows a fallback when a workflow exposes no topology", async () => {
    renderPanel(
      fake({ workflowsShow: async () => ({ ...summary, topology: null }) }),
    );
    expect(await screen.findByText(/no graph available/i)).toBeInTheDocument();
  });
});
