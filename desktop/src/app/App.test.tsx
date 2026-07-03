import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, within, act, waitFor } from "@testing-library/react";
import { App } from "./App";
import type { IpcClient } from "../ipc/client";
import type { RunParams, RunHandlers, RunResult } from "../ipc/types";

// A fake client good enough for the shell test: empty lists, no runs.
function fakeClient(): IpcClient {
  return {
    workflowsList: async () => [],
    workflowsShow: async () => ({
      name: "",
      title: "",
      description: "",
      topology: null,
    }),
    sessionsList: async () => [],
    sessionsShow: async () => ({ session: {} as never, events: [] }),
    decisionsList: async () => [],
    decisionsShow: async () => ({ record: {} as never, outcomes: [] }),
    connectorsList: async () => ({ connectors: [], problems: [] }),
    connectorsConfigList: async () => [],
    connectorsHealth: async () => ({ statuses: {}, problems: [] }),
    connectorsSync: async () => ({ results: [], problems: [] }),
    promptsList: async () => [],
    promptsShow: async () => ({ name: "", version: 0, text: "" }),
    promptsDiff: async () => ({ name: "", old: 0, new: 0, diff: "" }),
    memoryLessons: async () => [],
    run: async () => ({ status: "finished", session_id: "s" }),
    configGet: async () => ({
      model: "",
      provider: "",
      key_var: "",
      key_present: false,
      problems: [],
      settings: {
        debate_rounds: 2,
        judge_threshold: 0.7,
        judge_max_retries: 1,
        max_retries: 6,
      },
      origins: {
        model: "db",
        model_provider: "db",
        debate_rounds: "db",
        judge_threshold: "db",
        judge_max_retries: "db",
        max_retries: "db",
      },
      providers: [],
    }),
    configSet: async () => ({
      model: "",
      provider: "",
      key_var: "",
      key_present: false,
      problems: [],
      settings: {
        debate_rounds: 2,
        judge_threshold: 0.7,
        judge_max_retries: 1,
        max_retries: 6,
      },
      origins: {
        model: "db",
        model_provider: "db",
        debate_rounds: "db",
        judge_threshold: "db",
        judge_max_retries: "db",
        max_retries: "db",
      },
      providers: [],
    }),
    workspacesShow: async () => Promise.reject(new Error("not used in this test")),
    workspacesList: async () => [],
    approve: async () => ({ ok: true }),
    preferencesGet: async () => ({ theme: null }),
    preferencesSet: async (theme: string) => ({ theme }),
  } as unknown as IpcClient;
}

describe("App shell", () => {
  it("renders the nine nav items and defaults to the Run panel", async () => {
    render(<App client={fakeClient()} />);
    const nav = screen.getByRole("navigation", { name: "Sidebar" });
    for (const label of [
      "Run",
      "Workflows",
      "Sessions",
      "Decisions",
      "Memory",
      "Connectors",
      "Prompts",
      "Settings",
      "Reflection",
    ]) {
      expect(await within(nav).findByRole("button", { name: label })).toBeInTheDocument();
    }
    expect(screen.getByRole("heading", { name: /run a decision/i })).toBeInTheDocument();
  });

  it("switches to the Decisions panel on click", async () => {
    render(<App client={fakeClient()} />);
    fireEvent.click(within(screen.getByRole("navigation", { name: "Sidebar" })).getByRole("button", { name: "Decisions" }));
    expect(await screen.findByRole("heading", { name: /decision explorer/i })).toBeInTheDocument();
  });

  it("switches to the Connectors panel on click", async () => {
    render(<App client={fakeClient()} />);
    fireEvent.click(within(screen.getByRole("navigation", { name: "Sidebar" })).getByRole("button", { name: "Connectors" }));
    expect(await screen.findByRole("heading", { name: /^connectors$/i })).toBeInTheDocument();
  });

  it("switches to the Prompts panel on click", async () => {
    render(<App client={fakeClient()} />);
    fireEvent.click(within(screen.getByRole("navigation", { name: "Sidebar" })).getByRole("button", { name: "Prompts" }));
    expect(await screen.findByRole("heading", { name: /^prompts$/i })).toBeInTheDocument();
  });

  it("switches to the Workflows panel on click", async () => {
    render(<App client={fakeClient()} />);
    fireEvent.click(within(screen.getByRole("navigation", { name: "Sidebar" })).getByRole("button", { name: "Workflows" }));
    expect(await screen.findByRole("heading", { name: /^workflows$/i })).toBeInTheDocument();
  });

  it("switches to the Settings panel on click", async () => {
    render(<App client={fakeClient()} />);
    fireEvent.click(within(screen.getByRole("navigation", { name: "Sidebar" })).getByRole("button", { name: "Settings" }));
    expect(await screen.findByRole("heading", { name: /^settings$/i })).toBeInTheDocument();
  });

  it("switches to the Memory panel on click", async () => {
    render(<App client={fakeClient()} />);
    fireEvent.click(within(screen.getByRole("navigation", { name: "Sidebar" })).getByRole("button", { name: "Memory" }));
    expect(await screen.findByRole("heading", { name: /organizational memory/i })).toBeInTheDocument();
  });

  it("switches to the Reflection panel on click", async () => {
    render(<App client={fakeClient()} />);
    fireEvent.click(within(screen.getByRole("navigation", { name: "Sidebar" })).getByRole("button", { name: "Reflection" }));
    expect(await screen.findByRole("heading", { name: /^reflection$/i })).toBeInTheDocument();
  });

  it("shows a page description under the Run heading", async () => {
    render(<App client={fakeClient()} />);
    expect(await screen.findByText(/advisory pipeline/i)).toBeInTheDocument();
  });

  it("shows a live-run dot on the Run nav item while a run is in flight, and clears it when the run settles", async () => {
    let resolveRun!: (value: RunResult) => void;
    const client = fakeClient();
    client.run = (_params: RunParams, _handlers: RunHandlers) =>
      new Promise<RunResult>((resolve) => {
        resolveRun = resolve;
      });
    render(<App client={client} />);
    const main = screen.getByRole("main");
    fireEvent.change(within(main).getByLabelText("initiative"), { target: { value: "Test initiative" } });
    fireEvent.click(within(main).getByRole("button", { name: /^run$/i }));
    expect(await screen.findByLabelText("run in progress")).toBeInTheDocument();
    await act(async () => {
      resolveRun({ status: "finished", session_id: "s" });
    });
    await waitFor(() => expect(screen.queryByLabelText("run in progress")).toBeNull());
  });
});
