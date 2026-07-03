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

  it("marks a node running on ProgressEvent and done on NodeComplete", () => {
    const s = deriveNodeStatuses([
      ev("ProgressEvent", { node: "strategist" }),
    ]);
    expect(s.strategist).toBe("running");
    const s2 = deriveNodeStatuses([
      ev("ProgressEvent", { node: "strategist" }),
      ev("NodeComplete", { node: "strategist" }),
    ]);
    expect(s2.strategist).toBe("done");
  });

  it("marks a degraded node from a failed NodeComplete payload", () => {
    const s = deriveNodeStatuses([ev("NodeComplete", { node: "market", failed: true })]);
    expect(s.market).toBe("degraded");
  });

  it("flags the approval node awaiting-human", () => {
    const s = deriveNodeStatuses([ev("ApprovalRequested", { node: "human_approval" })]);
    expect(s.human_approval).toBe("awaiting-human");
  });

  it("returns an empty map for no events", () => {
    expect(deriveNodeStatuses([])).toEqual({});
  });
});
