import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { WorkflowsPanel } from "./WorkflowsPanel";
import { IpcProvider } from "../app/IpcProvider";
import type { IpcClient } from "../ipc/client";
import type { WorkflowSummary } from "../ipc/types";

const list: WorkflowSummary[] = [
  {
    name: "evaluate_initiative",
    title: "Evaluate Initiative",
    description: "Advisory pipeline: evidence → analysts → debate → strategist.",
  },
];

function fake(): IpcClient {
  return { workflowsList: async () => list } as unknown as IpcClient;
}

function renderPanel(client: IpcClient) {
  render(
    <IpcProvider client={client}>
      <WorkflowsPanel />
    </IpcProvider>,
  );
}

describe("WorkflowsPanel", () => {
  it("lists registered workflows with title and description", async () => {
    renderPanel(fake());
    expect(await screen.findByText("Evaluate Initiative")).toBeInTheDocument();
    expect(screen.getByText(/Advisory pipeline/)).toBeInTheDocument();
  });

  it("shows an empty state when there are no workflows", async () => {
    renderPanel({ workflowsList: async () => [] } as unknown as IpcClient);
    expect(await screen.findByText(/no workflows/i)).toBeInTheDocument();
  });
});
