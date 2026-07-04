import { describe, it, expect } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
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
function fake(overrides: Record<string, unknown> = {}): IpcClient {
  return {
    workflowsList: async () => [summary],
    workflowsShow: async () => detail,
    promptsList: async () => [{ name: "strategist", versions: [0], active: 0 }],
    promptsShow: async () => ({ name: "strategist", version: 0, text: "Decide." }),
    promptsSave: async () => ({ name: "strategist", versions: [0, 1], active: 1 }),
    ...overrides,
  } as unknown as IpcClient;
}
function renderPanel(client: IpcClient) {
  render(<IpcProvider client={client}><WorkflowsPanel /></IpcProvider>);
}

describe("WorkflowsPanel", () => {
  it("renders the selected workflow's graph as themed agent nodes", async () => {
    renderPanel(fake());
    expect(await screen.findByRole("button", { name: /Strategist/ })).toBeInTheDocument();
    expect(screen.getByText("Evaluate Initiative")).toBeInTheDocument();
  });

  it("shows an empty state when there are no workflows", async () => {
    renderPanel(fake({ workflowsList: async () => [] }));
    expect(await screen.findByText(/no workflows/i)).toBeInTheDocument();
  });

  it("shows a fallback when a workflow exposes no topology", async () => {
    renderPanel(fake({ workflowsShow: async () => ({ ...summary, topology: null }) }));
    expect(await screen.findByText(/no graph available/i)).toBeInTheDocument();
  });

  it("opens the prompt editor when an editable agent node is clicked", async () => {
    renderPanel(fake());
    fireEvent.click(await screen.findByRole("button", { name: /Strategist/ }));
    expect(await screen.findByDisplayValue("Decide.")).toBeInTheDocument();
  });

  it("opens the prompt editor on keyboard Enter, not just mouse click", async () => {
    renderPanel(fake());
    await screen.findByRole("button", { name: /Strategist/ });
    const rfNode = document.querySelector('[data-testid="rf__node-strategist"]') as HTMLElement;
    expect(rfNode).toBeTruthy();
    fireEvent.keyDown(rfNode, { key: "Enter" });
    expect(await screen.findByDisplayValue("Decide.")).toBeInTheDocument();
  });

  it("blocks switching nodes on unsaved prompt edits until the user confirms", async () => {
    const detailWithJudge: WorkflowDetail = {
      ...detail,
      topology: {
        nodes: [...detail.topology!.nodes, { id: "judge", prompts: ["judge"] }],
        edges: [...detail.topology!.edges, { source: "strategist", target: "judge", conditional: false }],
      },
    };
    renderPanel(fake({
      workflowsShow: async () => detailWithJudge,
      promptsList: async () => [
        { name: "strategist", versions: [0], active: 0 },
        { name: "judge", versions: [0], active: 0 },
      ],
      promptsShow: async (name: string) => ({ name, version: 0, text: name === "judge" ? "Score it." : "Decide." }),
    }));

    fireEvent.click(await screen.findByRole("button", { name: /Strategist/ }));
    const area = await screen.findByDisplayValue("Decide.");
    fireEvent.change(area, { target: { value: "Decide boldly." } });

    fireEvent.click(screen.getByRole("button", { name: /Judge/ }));
    expect((await screen.findAllByText("Discard unsaved prompt edits?")).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: /keep editing/i }));
    expect(await screen.findByDisplayValue("Decide boldly.")).toBeInTheDocument();
    expect(screen.queryByDisplayValue("Score it.")).not.toBeInTheDocument();
  });
});
