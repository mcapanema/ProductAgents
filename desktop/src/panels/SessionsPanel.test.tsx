import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SessionsPanel } from "./SessionsPanel";
import { IpcProvider } from "../app/IpcProvider";
import type { IpcClient } from "../ipc/client";
import type { SessionDetail, SessionSummary } from "../ipc/types";

const summary: SessionSummary = {
  id: "s1", workflow: "evaluate_initiative", status: "finished", created_at: "2026-06-28T00:00:00+00:00",
};
const detail: SessionDetail = {
  session: summary,
  events: [
    { type: "AnalystCompleted", payload: { node: "market", report: { analyst: "market", role: "M", findings: ["demand up"], signals: [], failed: false } } },
    { type: "FinalVerdict", payload: { verdict: "approve", rationale: "go", decided_by: "ai" } },
  ],
};

function fake(): IpcClient {
  return {
    sessionsList: async () => [summary],
    sessionsShow: async () => detail,
  } as unknown as IpcClient;
}

describe("SessionsPanel", () => {
  it("replays a persisted session as the stage timeline", async () => {
    render(
      <IpcProvider client={fake()}>
        <SessionsPanel />
      </IpcProvider>,
    );
    fireEvent.click(await screen.findByText("evaluate_initiative"));
    // The finished verdict is the active stage, open by default.
    await waitFor(() => expect(screen.getByText("Final Verdict")).toBeInTheDocument());
    // Analyst detail is collapsed behind its summary; expanding Market reveals its finding.
    fireEvent.click(screen.getByText("Market"));
    expect(screen.getByText("demand up")).toBeInTheDocument();
    expect(screen.getByText(/raw events \(2\)/i)).toBeInTheDocument();
  });
});
