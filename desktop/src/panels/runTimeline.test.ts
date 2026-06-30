import { describe, it, expect } from "vitest";
import { deriveStages } from "./runTimeline";
import type { IpcEvent } from "../ipc/types";

const by = (events: IpcEvent[], key: string) =>
  deriveStages(events).find((s) => s.key === key)!;

describe("deriveStages", () => {
  it("returns all 12 stages in pipeline order, all pending for an empty stream", () => {
    const stages = deriveStages([]);
    expect(stages.map((s) => s.key)).toEqual([
      "customer_research", "product_analytics", "market", "business", "technical",
      "recall", "debate", "strategist", "judge", "risk", "governance", "final",
    ]);
    expect(stages.every((s) => s.status === "pending")).toBe(true);
  });

  it("marks an analyst running on NodeProgress and done on AnalystCompleted", () => {
    const events: IpcEvent[] = [
      { type: "SessionStarted", payload: { workflow: "evaluate_initiative" } },
      { type: "NodeProgress", payload: { node: "market", message: "analyzing" } },
      {
        type: "AnalystCompleted",
        payload: { node: "market", report: { analyst: "market", role: "Market", findings: ["f1"], signals: ["s1"], failed: false } },
      },
    ];
    const market = by(events, "market");
    expect(market.status).toBe("done");
    expect(market.detail).toEqual({ kind: "analyst", report: { analyst: "market", role: "Market", findings: ["f1"], signals: ["s1"], failed: false } });
    expect(by(events, "customer_research").status).toBe("pending");
  });

  it("marks an analyst failed when its report.failed is true", () => {
    const events: IpcEvent[] = [
      { type: "AnalystCompleted", payload: { node: "technical", report: { analyst: "technical", role: "Tech", findings: [], signals: [], failed: true } } },
    ];
    expect(by(events, "technical").status).toBe("failed");
  });

  it("accumulates debate turns and promotes debate to done once the strategist runs", () => {
    const events: IpcEvent[] = [
      { type: "DebateTurnEmitted", payload: { round: 1, side: "advocate", argument: "ship it" } },
      { type: "DebateTurnEmitted", payload: { round: 1, side: "skeptic", argument: "risky" } },
      { type: "Recommended", payload: { recommendation: { recommendation: "ship", confidence: 0.8, rationale: "r", expected_outcomes: ["x"], failed: false } } },
    ];
    const debate = by(events, "debate");
    expect(debate.status).toBe("done"); // promoted: strategist became non-pending
    expect(debate.detail).toEqual({ kind: "debate", turns: [
      { round: 1, side: "advocate", argument: "ship it" },
      { round: 1, side: "skeptic", argument: "risky" },
    ] });
    expect(by(events, "strategist").status).toBe("done");
  });

  it("leaves debate running while turns stream with no later stage yet", () => {
    const events: IpcEvent[] = [
      { type: "DebateTurnEmitted", payload: { round: 1, side: "advocate", argument: "ship it" } },
    ];
    expect(by(events, "debate").status).toBe("running");
  });

  it("records recall lessons, judge scores, risk rows and governance", () => {
    const events: IpcEvent[] = [
      { type: "LessonsRecalled", payload: { lessons: ["ship betas"] } },
      { type: "Judged", payload: { passed: true, evidence_grounding_score: 0.9, rationale_coherence_score: 0.8, critique: "", attempt: 1 } },
      { type: "RiskAssessed", payload: { reviewer: "sec", role: "Security", level: "high", rationale: "pii" } },
      { type: "GovernanceAdvised", payload: { verdict: "approve", rationale: "ok" } },
    ];
    expect(by(events, "recall").detail).toEqual({ kind: "recall", lessons: ["ship betas"] });
    expect(by(events, "recall").status).toBe("done");
    expect(by(events, "judge").status).toBe("done");
    const risk = by(events, "risk");
    expect(risk.status).toBe("done"); // promoted: governance became non-pending
    expect(risk.detail).toEqual({ kind: "risk", rows: [{ reviewer: "sec", role: "Security", level: "high", rationale: "pii" }] });
    expect(by(events, "governance").detail).toEqual({ kind: "governance", verdict: "approve", rationale: "ok" });
  });

  it("drives the final stage through approval to verdict", () => {
    const awaiting = [{ type: "ApprovalRequested", payload: { advisory_verdict: "approve", advisory_rationale: "fine" } }];
    expect(by(awaiting, "final").status).toBe("running");
    const decided: IpcEvent[] = [
      ...awaiting,
      { type: "FinalVerdict", payload: { verdict: "approve", rationale: "go", decided_by: "human" } },
    ];
    const final = by(decided, "final");
    expect(final.status).toBe("done");
    expect(final.detail).toEqual({ kind: "final", verdict: "approve", rationale: "go", decidedBy: "human" });
  });

  it("marks SessionFinished as final done in an autonomous run", () => {
    expect(by([{ type: "SessionFinished", payload: { recommendation: null } }], "final").status).toBe("done");
  });

  it("marks a node failed on NodeFailed and SessionFailed", () => {
    expect(by([{ type: "NodeFailed", payload: { node: "business", message: "boom" } }], "business").status).toBe("failed");
    expect(by([{ type: "SessionFailed", payload: { node: "judge", category: "rate_limit", message: "429" } }], "judge").status).toBe("failed");
  });

  it("never downgrades a done analyst to running on a late NodeProgress", () => {
    const events: IpcEvent[] = [
      { type: "AnalystCompleted", payload: { node: "market", report: { analyst: "market", role: "M", findings: [], signals: [], failed: false } } },
      { type: "NodeProgress", payload: { node: "market", message: "late" } },
    ];
    expect(by(events, "market").status).toBe("done");
  });
});
