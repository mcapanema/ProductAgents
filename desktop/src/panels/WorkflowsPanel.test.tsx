import { describe, it, expect } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { WorkflowsPanel } from "./WorkflowsPanel";
import { IpcProvider } from "../app/IpcProvider";
import type { IpcClient } from "../ipc/client";
import type { WorkflowDefinitionDTO, WorkflowDetail, WorkflowSummary } from "../ipc/types";

const summary: WorkflowSummary = {
  name: "evaluate_initiative",
  title: "Evaluate Initiative",
  description: "Advisory pipeline: evidence → analysts → debate → strategist.",
};
const definition: WorkflowDefinitionDTO = {
  name: summary.name,
  title: summary.title,
  description: summary.description,
  nodes: [{ id: "strategist", kind: "strategist", config: {} }],
  edges: [
    { source: "__start__", target: "strategist", conditional: false },
    { source: "strategist", target: "__end__", conditional: true },
  ],
  layout: {},
  builtin: true,
};
const detail: WorkflowDetail = {
  ...summary,
  definition,
  topology: {
    nodes: [
      { id: "__start__", prompts: [], kind: "__start__", config: {} },
      { id: "strategist", prompts: ["strategist"], kind: "strategist", config: {} },
      { id: "__end__", prompts: [], kind: "__end__", config: {} },
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
    workflowsPalette: async () => [],
    workflowsSave: async () => summary,
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

  it("closing the prompt drawer keeps it closed", async () => {
    // Regression: React Flow re-invokes onSelectionChange on every parent
    // render (not just on an actual selection change). An unmemoized handler
    // kept re-reading the *stale* still-selected node and reopening the
    // drawer the instant it closed — closing never stuck.
    renderPanel(fake());
    fireEvent.click(await screen.findByRole("button", { name: /Strategist/ }));
    expect(await screen.findByDisplayValue("Decide.")).toBeInTheDocument();

    const closeButton = document.querySelector(".ant-drawer-close") as HTMLElement;
    expect(closeButton).toBeTruthy();
    fireEvent.click(closeButton);
    await waitFor(() => expect(screen.queryByDisplayValue("Decide.")).not.toBeInTheDocument());

    // Let any pending effects (e.g. the drawer's own state-reset effect,
    // which itself triggers a parent re-render via onDirtyChange) settle,
    // then confirm the drawer is still closed rather than having reopened.
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(screen.queryByDisplayValue("Decide.")).not.toBeInTheDocument();
  });

  it("blocks switching nodes on unsaved prompt edits until the user confirms", async () => {
    const detailWithJudge: WorkflowDetail = {
      ...detail,
      topology: {
        nodes: [...detail.topology!.nodes, { id: "judge", prompts: ["judge"], kind: "judge", config: {} }],
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

  it("adds a node from the palette and saves the resulting flow", async () => {
    const saved: WorkflowDefinitionDTO[] = [];
    renderPanel(fake({
      workflowsPalette: async () => [
        { kind: "market", label: "Market", role: "Analyst", singleton: false, prompts: ["market"], reads: [], writes: [] },
      ],
      workflowsSave: async (defn: WorkflowDefinitionDTO) => {
        saved.push(defn);
        return summary;
      },
    }));

    fireEvent.click(await screen.findByRole("button", { name: /Market/ }));
    fireEvent.click(await screen.findByRole("button", { name: /^save$/i }));

    await waitFor(() => expect(saved).toHaveLength(1));
    expect(saved[0].nodes.some((n) => n.id === "market" && n.kind === "market")).toBe(true);
    expect(await screen.findByText(/workflow saved/i)).toBeInTheDocument();
  });

  it("surfaces a server-side save error instead of failing silently", async () => {
    renderPanel(fake({
      workflowsPalette: async () => [
        { kind: "market", label: "Market", role: "Analyst", singleton: false, prompts: ["market"], reads: [], writes: [] },
      ],
      workflowsSave: async () => { throw new Error("edge target 'market' has no route to __end__"); },
    }));

    fireEvent.click(await screen.findByRole("button", { name: /Market/ }));
    fireEvent.click(await screen.findByRole("button", { name: /^save$/i }));

    expect(await screen.findByText(/no route to __end__/)).toBeInTheDocument();
  });
});
