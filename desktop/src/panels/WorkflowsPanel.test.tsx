import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { WorkflowsPanel } from "./WorkflowsPanel";
import { IpcProvider } from "../app/IpcProvider";
import type { IpcClient } from "../ipc/client";
import type { WorkflowDetail, WorkflowSummary } from "../ipc/types";

// Regression: `flowNodes` used to be set one render behind `flowEdges` (nodes
// via a useEffect, edges computed inline every render), so React Flow could
// receive a real `edges` array pointing at node ids that weren't in `nodes`
// yet and silently drop them. Spy on every prop set `<ReactFlow>` receives
// and assert edges never appear before their nodes do.
const { reactFlowCalls } = vi.hoisted(() => ({
  reactFlowCalls: [] as { nodes: number; edges: number }[],
}));
vi.mock("@xyflow/react", async () => {
  const actual = await vi.importActual<typeof import("@xyflow/react")>("@xyflow/react");
  return {
    ...actual,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ReactFlow: (props: any) => {
      reactFlowCalls.push({ nodes: props.nodes.length, edges: props.edges.length });
      return <actual.ReactFlow {...props} />;
    },
  };
});

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
  it("never passes ReactFlow edges before their nodes exist", async () => {
    reactFlowCalls.length = 0;
    renderPanel(fake());
    await screen.findByRole("button", { name: /Strategist/ });
    expect(reactFlowCalls.length).toBeGreaterThan(0);
    for (const call of reactFlowCalls) {
      if (call.edges > 0) expect(call.nodes).toBeGreaterThan(0);
    }
    // Sanity: the settled state actually has both, not just "never disagreed
    // because neither ever loaded."
    expect(reactFlowCalls[reactFlowCalls.length - 1]).toEqual({ nodes: 3, edges: 2 });
  });

  it("renders the selected workflow's graph as themed agent nodes", async () => {
    renderPanel(fake());
    expect(await screen.findByRole("button", { name: /Strategist/ })).toBeInTheDocument();
    expect(screen.getByText("Evaluate Initiative", { selector: "strong" })).toBeInTheDocument();
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

  it("switches the inspected workflow via the selector", async () => {
    const second: WorkflowSummary = { name: "roadmap", title: "Roadmap Prioritization", description: "b" };
    const show = vi.fn(async (name: string) =>
      name === "roadmap" ? { ...second, topology: null } : detail,
    );
    renderPanel(fake({ workflowsList: async () => [summary, second], workflowsShow: show }));
    // First workflow's graph renders on load.
    await screen.findByRole("button", { name: /Strategist/ });
    fireEvent.mouseDown(screen.getByRole("combobox", { name: "workflow" }));
    fireEvent.click(await screen.findByTitle("Roadmap Prioritization"));
    await waitFor(() => expect(show).toHaveBeenCalledWith("roadmap"));
  });
});
