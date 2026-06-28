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
});
