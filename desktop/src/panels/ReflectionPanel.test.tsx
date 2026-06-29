import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ReflectionPanel } from "./ReflectionPanel";
import { IpcProvider } from "../app/IpcProvider";
import type { IpcClient } from "../ipc/client";
import type { DecisionSummary, OutcomeRecord } from "../ipc/types";

const decisions: DecisionSummary[] = [
  { id: "dec-1", title: "Add SSO", recommendation: "Build it", confidence: 0.8, created_at: "t" },
];

const outcome: OutcomeRecord = {
  decision_id: "dec-1",
  actual_outcomes: ["slow adoption"],
  prediction_accuracy: 0.4,
  lessons_learned: ["validate demand earlier"],
  reflected_at: "t",
  failed: false,
};

function renderPanel(client: IpcClient) {
  render(
    <IpcProvider client={client}>
      <ReflectionPanel />
    </IpcProvider>,
  );
}

describe("ReflectionPanel", () => {
  it("lists past decisions to reflect on", async () => {
    renderPanel({ decisionsList: async () => decisions } as unknown as IpcClient);
    expect(await screen.findByText(/Add SSO/)).toBeInTheDocument();
  });

  it("records an outcome and shows the result", async () => {
    const reflectionRecord = vi.fn(async () => outcome);
    renderPanel({
      decisionsList: async () => decisions,
      reflectionRecord,
    } as unknown as IpcClient);
    await screen.findByText(/Add SSO/);

    fireEvent.change(screen.getByLabelText(/decision/i), { target: { value: "dec-1" } });
    fireEvent.change(screen.getByLabelText(/what happened/i), { target: { value: "shipped" } });
    fireEvent.click(screen.getByRole("button", { name: /reflect/i }));

    await waitFor(() => expect(reflectionRecord).toHaveBeenCalledWith("dec-1", "shipped"));
    expect(await screen.findByText(/slow adoption/)).toBeInTheDocument();
    expect(screen.getByText(/validate demand earlier/)).toBeInTheDocument();
  });

  it("degrades when decisions fail to load", async () => {
    renderPanel({ decisionsList: async () => { throw new Error("down"); } } as unknown as IpcClient);
    expect(await screen.findByText(/no decisions/i)).toBeInTheDocument();
  });
});
