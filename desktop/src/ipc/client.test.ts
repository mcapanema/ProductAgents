import { describe, it, expect } from "vitest";
import { IpcClient } from "./client";
import type { IpcMessage } from "./types";

function harness() {
  const sent: string[] = [];
  let cb: (m: IpcMessage) => void = () => {};
  const client = new IpcClient(
    async (line: string) => {
      sent.push(line);
    },
    (fn) => {
      cb = fn;
    },
  );
  return { client, sent, emit: (m: IpcMessage) => cb(m) };
}

describe("IpcClient", () => {
  it("sends a request with an incrementing id and correlates the result", async () => {
    const { client, sent, emit } = harness();
    const p = client.decisionsList();
    expect(JSON.parse(sent[0])).toMatchObject({ id: 1, method: "decisions.list" });
    emit({ id: 1, result: [{ id: "d1" }] });
    expect(await p).toEqual([{ id: "d1" }]);
  });

  it("passes params through", async () => {
    const { client, sent } = harness();
    void client.decisionsShow("d9");
    expect(JSON.parse(sent[0])).toMatchObject({
      id: 1,
      method: "decisions.show",
      params: { decision_id: "d9" },
    });
  });

  it("rejects when the server returns an error message", async () => {
    const { client, emit } = harness();
    const p = client.sessionsShow("missing");
    emit({ id: 1, error: "no such session: missing" });
    await expect(p).rejects.toThrow("no such session: missing");
  });

  it("streams run events to the handler, then resolves on the terminal result", async () => {
    const { client, emit } = harness();
    const events: { type: string }[] = [];
    const p = client.run(
      { workflow: "evaluate_initiative", title: "X" },
      { onEvent: (e) => events.push(e) },
    );
    emit({ id: 1, event: { type: "SessionStarted", payload: {} } });
    emit({ id: 1, event: { type: "NodeProgress", payload: { node: "market" } } });
    emit({ id: 1, result: { status: "finished", session_id: "s1" } });
    expect(events.map((e) => e.type)).toEqual(["SessionStarted", "NodeProgress"]);
    expect(await p).toEqual({ status: "finished", session_id: "s1" });
  });

  it("does not deliver events for an unrelated id", async () => {
    const { client, emit } = harness();
    const events: unknown[] = [];
    void client.run({ workflow: "w", title: "X" }, { onEvent: (e) => events.push(e) });
    emit({ id: 999, event: { type: "Stray", payload: {} } });
    expect(events).toEqual([]);
  });
});
