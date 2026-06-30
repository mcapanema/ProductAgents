import { describe, it, expect } from "vitest";
import { runReducer, initialRunState } from "./runReducer";

describe("runReducer", () => {
  it("starts a run: clears events, marks running", () => {
    const s = runReducer(initialRunState, { kind: "start" });
    expect(s.status).toBe("running");
    expect(s.events).toEqual([]);
  });

  it("appends streamed events while running", () => {
    let s = runReducer(initialRunState, { kind: "start" });
    s = runReducer(s, { kind: "event", event: { type: "SessionStarted", payload: {} } });
    s = runReducer(s, { kind: "event", event: { type: "NodeProgress", payload: { node: "market" } } });
    expect(s.events.map((e) => e.type)).toEqual(["SessionStarted", "NodeProgress"]);
  });

  it("records the terminal result and stops running", () => {
    let s = runReducer(initialRunState, { kind: "start" });
    s = runReducer(s, { kind: "done", result: { status: "finished", session_id: "s1" } });
    expect(s.status).toBe("finished");
    expect(s.sessionId).toBe("s1");
  });

  it("captures an error and stops running", () => {
    let s = runReducer(initialRunState, { kind: "start" });
    s = runReducer(s, { kind: "error", message: "rate limited" });
    expect(s.status).toBe("error");
    expect(s.error).toBe("rate limited");
  });

  it("enters the awaiting state on an ApprovalRequested event", () => {
    const started = runReducer(initialRunState, { kind: "start" });
    const next = runReducer(started, {
      kind: "event",
      event: { type: "ApprovalRequested", payload: { advisory_verdict: "approve", advisory_rationale: "looks fine" } },
    });
    expect(next.awaiting).toBe(true);
    expect(next.advisory).toEqual({ verdict: "approve", rationale: "looks fine" });
  });

  it("leaves the awaiting state on a FinalVerdict event", () => {
    let s = runReducer(initialRunState, { kind: "start" });
    s = runReducer(s, { kind: "event", event: { type: "ApprovalRequested", payload: {} } });
    s = runReducer(s, { kind: "event", event: { type: "FinalVerdict", payload: { verdict: "approve" } } });
    expect(s.awaiting).toBe(false);
  });

  it("clears awaiting immediately on approved", () => {
    let s = runReducer(initialRunState, { kind: "start" });
    s = runReducer(s, { kind: "event", event: { type: "ApprovalRequested", payload: {} } });
    s = runReducer(s, { kind: "approved" });
    expect(s.awaiting).toBe(false);
  });

  it("captures the session id from a streamed event", () => {
    let s = runReducer(initialRunState, { kind: "start" });
    s = runReducer(s, { kind: "event", event: { type: "SessionStarted", payload: { session_id: "sx" } } });
    expect(s.sessionId).toBe("sx");
  });

  it("marks cancelling on the cancel action", () => {
    let s = runReducer(initialRunState, { kind: "start" });
    s = runReducer(s, { kind: "cancel" });
    expect(s.cancelling).toBe(true);
  });

  it("records a cancelled terminal result", () => {
    let s = runReducer(initialRunState, { kind: "start" });
    s = runReducer(s, { kind: "done", result: { status: "cancelled", session_id: "sx" } });
    expect(s.status).toBe("cancelled");
    expect(s.cancelling).toBe(false);
  });
});
