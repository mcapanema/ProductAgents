import { render, screen } from "@testing-library/react";
import { StageTimeline } from "./StageTimeline";
import type { IpcEvent } from "../ipc/types";
import { deriveStages } from "./runTimeline";

describe("StageTimeline", () => {
  it("renders all stage labels on empty run", () => {
    render(<StageTimeline stages={deriveStages([])} />);
    expect(screen.getByText("Final Verdict")).toBeInTheDocument();
  });

  it("shows recommendation and risk detail", () => {
    const events: IpcEvent[] = [
      {
        type: "Recommended",
        payload: {
          recommendation: {
            recommendation: "ship it",
            confidence: 0.82,
            rationale: "strong signals",
            expected_outcomes: [],
            failed: false,
          },
        },
      },
      {
        type: "RiskAssessed",
        payload: { reviewer: "Security", role: "sec", level: "ok", rationale: "pii" },
      },
    ];
    render(<StageTimeline stages={deriveStages(events)} />);
    expect(screen.getByText("ship it")).toBeInTheDocument();
    expect(screen.getByText("82%")).toBeInTheDocument();
    expect(screen.getByText("pii")).toBeInTheDocument();
    expect(screen.getByText("ok")).toBeInTheDocument();
  });
});
