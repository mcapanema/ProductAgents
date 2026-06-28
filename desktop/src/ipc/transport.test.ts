import { describe, it, expect, afterEach } from "vitest";
import { isTauri, createWsClient } from "./transport";

describe("isTauri", () => {
  afterEach(() => {
    delete (window as unknown as Record<string, unknown>).__TAURI_INTERNALS__;
  });

  it("is false in a plain browser (no Tauri internals)", () => {
    expect(isTauri()).toBe(false);
  });

  it("is true when Tauri injects its internals", () => {
    (window as unknown as Record<string, unknown>).__TAURI_INTERNALS__ = {};
    expect(isTauri()).toBe(true);
  });
});

// Minimal fake WebSocket: fires onopen on the next tick, records sends, lets the
// test push inbound messages. Mirrors enough of the WebSocket surface for the client.
class FakeWebSocket {
  static last: FakeWebSocket;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  sent: string[] = [];

  constructor(public url: string) {
    FakeWebSocket.last = this;
    setTimeout(() => this.onopen?.(), 0); // resolve after createWsClient sets onopen
  }

  send(line: string): void {
    this.sent.push(line);
  }

  receive(message: unknown): void {
    this.onmessage?.({ data: JSON.stringify(message) });
  }
}

describe("createWsClient", () => {
  it("connects, sends requests, and correlates responses over the socket", async () => {
    const client = await createWsClient(
      "ws://test",
      FakeWebSocket as unknown as typeof WebSocket,
    );
    const socket = FakeWebSocket.last;

    const pending = client.decisionsList();
    expect(JSON.parse(socket.sent[0])).toMatchObject({
      id: 1,
      method: "decisions.list",
    });

    socket.receive({ id: 1, result: [{ id: "d1" }] });
    expect(await pending).toEqual([{ id: "d1" }]);
  });

  it("ignores a non-JSON frame instead of crashing", async () => {
    const client = await createWsClient(
      "ws://test",
      FakeWebSocket as unknown as typeof WebSocket,
    );
    const socket = FakeWebSocket.last;
    const pending = client.workflowsList();

    socket.onmessage?.({ data: "not json" }); // must not throw
    socket.receive({ id: 1, result: [] });
    expect(await pending).toEqual([]);
  });
});
