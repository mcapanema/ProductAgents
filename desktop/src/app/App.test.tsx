import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
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
    run: async () => ({ status: "finished", session_id: "s" }),
  } as unknown as IpcClient;
}

describe("App shell", () => {
  it("renders the three nav items and defaults to the Run panel", () => {
    render(<App client={fakeClient()} />);
    expect(screen.getByRole("button", { name: "Run" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sessions" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Decisions" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /run a decision/i })).toBeInTheDocument();
  });

  it("switches to the Decisions panel on click", async () => {
    render(<App client={fakeClient()} />);
    fireEvent.click(screen.getByRole("button", { name: "Decisions" }));
    expect(await screen.findByRole("heading", { name: /decision explorer/i })).toBeInTheDocument();
  });
});
