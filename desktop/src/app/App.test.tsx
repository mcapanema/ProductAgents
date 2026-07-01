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
    promptsList: async () => [],
    promptsShow: async () => ({ name: "", version: 0, text: "" }),
    promptsDiff: async () => ({ name: "", old: 0, new: 0, diff: "" }),
    run: async () => ({ status: "finished", session_id: "s" }),
    configGet: async () => ({
      model: "",
      provider: "",
      key_var: "",
      key_present: false,
      problems: [],
      providers: [],
    }),
    configSet: async () => ({
      model: "",
      provider: "",
      key_var: "",
      key_present: false,
      problems: [],
      providers: [],
    }),
    approve: async () => ({ ok: true }),
  } as unknown as IpcClient;
}

describe("App shell", () => {
  it("renders the seven nav items and defaults to the Run panel", async () => {
    render(<App client={fakeClient()} />);
    const nav = screen.getByRole("navigation");
    for (const label of ["Run", "Workflows", "Sessions", "Decisions", "Connectors", "Prompts", "Settings"]) {
      expect(await within(nav).findByRole("menuitem", { name: label })).toBeInTheDocument();
    }
    expect(screen.getByRole("heading", { name: /run a decision/i })).toBeInTheDocument();
  });

  it("switches to the Decisions panel on click", async () => {
    render(<App client={fakeClient()} />);
    fireEvent.click(within(screen.getByRole("navigation")).getByRole("menuitem", { name: "Decisions" }));
    expect(await screen.findByRole("heading", { name: /decision explorer/i })).toBeInTheDocument();
  });

  it("switches to the Connectors panel on click", async () => {
    render(<App client={fakeClient()} />);
    fireEvent.click(within(screen.getByRole("navigation")).getByRole("menuitem", { name: "Connectors" }));
    expect(await screen.findByRole("heading", { name: /^connectors$/i })).toBeInTheDocument();
  });

  it("switches to the Prompts panel on click", async () => {
    render(<App client={fakeClient()} />);
    fireEvent.click(within(screen.getByRole("navigation")).getByRole("menuitem", { name: "Prompts" }));
    expect(await screen.findByRole("heading", { name: /^prompts$/i })).toBeInTheDocument();
  });

  it("switches to the Workflows panel on click", async () => {
    render(<App client={fakeClient()} />);
    fireEvent.click(within(screen.getByRole("navigation")).getByRole("menuitem", { name: "Workflows" }));
    expect(await screen.findByRole("heading", { name: /^workflows$/i })).toBeInTheDocument();
  });

  it("switches to the Settings panel on click", async () => {
    render(<App client={fakeClient()} />);
    fireEvent.click(within(screen.getByRole("navigation")).getByRole("menuitem", { name: "Settings" }));
    expect(await screen.findByRole("heading", { name: /^settings$/i })).toBeInTheDocument();
  });
});
