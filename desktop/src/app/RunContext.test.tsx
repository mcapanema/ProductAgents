import { describe, it, expect, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { IpcProvider } from "./IpcProvider";
import { RunProvider, useRun } from "./RunContext";
import type { IpcClient } from "../ipc/client";
import type { RunHandlers, RunParams } from "../ipc/types";

function wrapper(client: IpcClient) {
  return ({ children }: { children: ReactNode }) => (
    <IpcProvider client={client}>
      <RunProvider>{children}</RunProvider>
    </IpcProvider>
  );
}

describe("RunProvider", () => {
  it("start() drives ipc.run and reduces state to finished", async () => {
    const run = vi.fn(async () => ({ status: "finished" as const, session_id: "s" }));
    const { result } = renderHook(() => useRun(), {
      wrapper: wrapper({ run } as unknown as IpcClient),
    });
    await act(async () => {
      await result.current.start({ workflow: "w", title: "T" });
    });
    expect(run).toHaveBeenCalled();
    await waitFor(() => expect(result.current.state.status).toBe("finished"));
  });

  it("feeds streamed events into the reducer", async () => {
    const run = vi.fn((_p: RunParams, handlers: RunHandlers) => {
      handlers.onEvent({ type: "SessionStarted", payload: { session_id: "sx" } });
      return new Promise<{ status: "finished"; session_id: string }>(() => {});
    });
    const { result } = renderHook(() => useRun(), {
      wrapper: wrapper({ run } as unknown as IpcClient),
    });
    await act(async () => {
      result.current.start({ workflow: "w", title: "T" });
    });
    await waitFor(() => expect(result.current.state.sessionId).toBe("sx"));
    expect(result.current.state.status).toBe("running");
  });

  it("cancel() sends run.cancel for the active session", async () => {
    const runCancel = vi.fn(async () => ({ ok: true }));
    const run = vi.fn((_p: RunParams, handlers: RunHandlers) => {
      handlers.onEvent({ type: "SessionStarted", payload: { session_id: "sx" } });
      return new Promise<{ status: "finished"; session_id: string }>(() => {});
    });
    const { result } = renderHook(() => useRun(), {
      wrapper: wrapper({ run, runCancel } as unknown as IpcClient),
    });
    await act(async () => {
      result.current.start({ workflow: "w", title: "T" });
    });
    await waitFor(() => expect(result.current.state.sessionId).toBe("sx"));
    await act(async () => {
      await result.current.cancel();
    });
    expect(runCancel).toHaveBeenCalledWith("sx");
  });
});
