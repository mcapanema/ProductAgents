import { describe, it, expect } from "vitest";
import { formatConfidence, predictionRows, decisionSections } from "./decisionView";
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
    evidence_sources: [
      { field: "customer_feedback", source: "scenario:sample", location: "feedback.txt" },
    ],
    debate: [{ round: 1, side: "advocate", argument: "ship now" }],
    risks: [{ reviewer: "Risk", role: "reviewer", level: "low", rationale: "cheap" }],
    governance: { verdict: "approve", rationale: "ok", decided_by: "ai" },
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

describe("decisionSections", () => {
  it("surfaces evidence, debate, risks and governance from the record", () => {
    const s = decisionSections(detail);
    expect(s.evidence.map((e) => e.field)).toEqual(["customer_feedback"]);
    expect(s.debate[0].side).toBe("advocate");
    expect(s.risks[0].level).toBe("low");
    expect(s.governance?.verdict).toBe("approve");
  });

  it("degrades to empty/null when fields are absent", () => {
    const bare = { record: { ...detail.record, evidence_sources: undefined, debate: undefined, risks: undefined, governance: undefined }, outcomes: [] } as unknown as DecisionDetail;
    const s = decisionSections(bare);
    expect(s.evidence).toEqual([]);
    expect(s.debate).toEqual([]);
    expect(s.risks).toEqual([]);
    expect(s.governance).toBeNull();
  });
});
