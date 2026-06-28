import { describe, it, expect } from "vitest";
import { formatConfidence, predictionRows } from "./decisionView";
import type { DecisionDetail } from "../ipc/types";

const detail: DecisionDetail = {
  record: {
    decision_id: "d1",
    initiative: { title: "New API", description: "x" },
    recommendation: {
      recommendation: "ship it",
      confidence: 0.82,
      rationale: "because",
      expected_outcomes: ["adoption up", "support down"],
    },
    timestamp: "2026-06-28T00:00:00+00:00",
  },
  outcomes: [
    {
      decision_id: "d1",
      actual_outcomes: ["adoption flat"],
      prediction_accuracy: 0.4,
      lessons_learned: ["scope smaller", "ship a beta first"],
      reflected_at: "2026-06-29T00:00:00+00:00",
    },
  ],
};

describe("decisionView", () => {
  it("formats confidence as a percentage", () => {
    expect(formatConfidence(0.82)).toBe("82%");
    expect(formatConfidence(1)).toBe("100%");
  });

  it("collects predicted, actual outcomes and lessons across reflections", () => {
    const rows = predictionRows(detail);
    expect(rows.predicted).toEqual(["adoption up", "support down"]);
    expect(rows.actual).toEqual(["adoption flat"]);
    expect(rows.lessons).toEqual(["scope smaller", "ship a beta first"]);
  });

  it("handles a decision with no reflections yet", () => {
    const rows = predictionRows({ ...detail, outcomes: [] });
    expect(rows.actual).toEqual([]);
    expect(rows.lessons).toEqual([]);
  });
});
