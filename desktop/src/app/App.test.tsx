import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { App } from "./App";
import type { IpcClient } from "../ipc/client";

// A fake client good enough for the shell test: empty lists, no runs.
function fakeClient(): IpcClient {
  return {
    workflowsList: async () => [],
    sessionsList: async () => [],
    sessionsShow: async () => ({ session: {} as never, events: [] }),
    decisionsList: async () => [],
    decisionsShow: async () => ({ record: {} as never, outcomes: [] }),
    connectorsList: async () => ({ connectors: [], problems: [] }),
    connectorsHealth: async () => ({ statuses: {}, problems: [] }),
    connectorsSync: async () => ({ results: [], problems: [] }),
    run: async () => ({ status: "finished", session_id: "s" }),
  } as unknown as IpcClient;
}

describe("App shell", () => {
  it("renders the four nav items and defaults to the Run panel", () => {
    render(<App client={fakeClient()} />);
    const nav = screen.getByRole("navigation");
    expect(within(nav).getByRole("button", { name: "Run" })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: "Sessions" })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: "Decisions" })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: "Connectors" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /run a decision/i })).toBeInTheDocument();
  });

  it("switches to the Decisions panel on click", async () => {
    render(<App client={fakeClient()} />);
    fireEvent.click(within(screen.getByRole("navigation")).getByRole("button", { name: "Decisions" }));
    expect(await screen.findByRole("heading", { name: /decision explorer/i })).toBeInTheDocument();
  });

  it("switches to the Connectors panel on click", async () => {
    render(<App client={fakeClient()} />);
    fireEvent.click(within(screen.getByRole("navigation")).getByRole("button", { name: "Connectors" }));
    expect(await screen.findByRole("heading", { name: /^connectors$/i })).toBeInTheDocument();
  });
});
