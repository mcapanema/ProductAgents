import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { DecisionsPanel } from "./DecisionsPanel";
import { IpcProvider } from "../app/IpcProvider";
import type { IpcClient } from "../ipc/client";
import type { DecisionDetail, DecisionSummary } from "../ipc/types";

const summary: DecisionSummary = {
  id: "d1", title: "New API", recommendation: "ship it",
  confidence: 0.8, created_at: "2026-06-28T00:00:00+00:00",
};
const detail: DecisionDetail = {
  record: {
    decision_id: "d1",
    initiative: { title: "New API", description: "x" },
    recommendation: {
      recommendation: "ship it", confidence: 0.8, rationale: "because",
      expected_outcomes: ["adoption up"],
    },
    timestamp: "2026-06-28T00:00:00+00:00",
  },
  outcomes: [{
    decision_id: "d1", actual_outcomes: ["adoption flat"], prediction_accuracy: 0.4,
    lessons_learned: ["scope smaller"], reflected_at: "2026-06-29T00:00:00+00:00",
  }],
};

function fake(): IpcClient {
  return {
    decisionsList: async () => [summary],
    decisionsShow: async () => detail,
  } as unknown as IpcClient;
}

describe("DecisionsPanel", () => {
  it("lists decisions then shows predicted vs actual on click", async () => {
    render(
      <IpcProvider client={fake()}>
        <DecisionsPanel />
      </IpcProvider>,
    );
    const item = await screen.findByText("New API");
    fireEvent.click(item);
    await waitFor(() => expect(screen.getByText("adoption up")).toBeInTheDocument());
    expect(screen.getByText("adoption flat")).toBeInTheDocument();
    expect(screen.getByText("scope smaller")).toBeInTheDocument();
  });

  it("decision rows are keyboard-operable buttons", async () => {
    render(
      <IpcProvider client={fake()}>
        <DecisionsPanel />
      </IpcProvider>,
    );
    const row = await screen.findByRole("button", { name: /new api/i });
    row.focus();
    fireEvent.keyDown(row, { key: "Enter" }); // native <button> activates on Enter
    fireEvent.click(row); // native button: Enter/Space dispatch click
    expect(await screen.findByText("adoption up")).toBeInTheDocument();
  });
});
