import { describe, it, expect } from "vitest";
import { statusStyle, deriveNodeStatuses } from "./nodeStatus";
import type { IpcEvent } from "../ipc/types";

describe("statusStyle", () => {
  it("pulses only while running", () => {
    expect(statusStyle("running").pulse).toBe(true);
    expect(statusStyle("done").pulse).toBe(false);
  });
  it("maps each status to token var() strings", () => {
    expect(statusStyle("failed").border).toContain("var(--ai-failed");
    expect(statusStyle("idle").border).toContain("var(--ai-node-border");
  });
});

describe("deriveNodeStatuses", () => {
  const ev = (type: string, payload: Record<string, unknown> = {}): IpcEvent => ({ type, payload });

  it("marks a node running on NodeProgress and done on AnalystCompleted", () => {
    const s = deriveNodeStatuses([
      ev("NodeProgress", { node: "customer_research", message: "working" }),
    ]);
    expect(s.customer_research).toBe("running");
    const s2 = deriveNodeStatuses([
      ev("NodeProgress", { node: "customer_research", message: "working" }),
      ev("AnalystCompleted", { node: "customer_research", report: {} }),
    ]);
    expect(s2.customer_research).toBe("done");
  });

  it("marks a degraded node from NodeFailed", () => {
    const s = deriveNodeStatuses([ev("NodeFailed", { node: "strategist", message: "transient error" })]);
    expect(s.strategist).toBe("degraded");
  });

  it("marks a failed node from SessionFailed", () => {
    const s = deriveNodeStatuses([
      ev("SessionFailed", { node: "strategist", category: "rate_limit", message: "boom" }),
    ]);
    expect(s.strategist).toBe("failed");
  });

  it("flags the approval node awaiting-human regardless of payload", () => {
    const s = deriveNodeStatuses([
      ev("ApprovalRequested", { advisory_verdict: "approve", advisory_rationale: "looks good" }),
    ]);
    expect(s.human_approval).toBe("awaiting-human");
  });

  it("returns an empty map for no events", () => {
    expect(deriveNodeStatuses([])).toEqual({});
  });
});
