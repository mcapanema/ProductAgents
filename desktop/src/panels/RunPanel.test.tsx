import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { RunPanel } from "./RunPanel";
import { IpcProvider } from "../app/IpcProvider";
import type { IpcClient } from "../ipc/client";
import type { RunHandlers, RunParams, IpcEvent } from "../ipc/types";

describe("RunPanel approval flow", () => {
  it("passes approval=true when the checkbox is checked", async () => {
    const run = vi.fn(async (_p: RunParams, _h: RunHandlers) => ({ status: "finished" as const, session_id: "s" }));
    render(
      <IpcProvider client={{ run } as unknown as IpcClient}>
        <RunPanel />
      </IpcProvider>,
    );
    fireEvent.change(screen.getByLabelText("initiative"), { target: { value: "New API" } });
    fireEvent.click(screen.getByLabelText(/require approval/i));
    fireEvent.click(screen.getByRole("button", { name: "Run" }));
    await waitFor(() => expect(run).toHaveBeenCalled());
    expect(run.mock.calls[0][0]).toMatchObject({ approval: true, title: "New API" });
  });

  it("shows approve buttons on ApprovalRequested and sends the verdict", async () => {
    const approve = vi.fn(async () => ({ ok: true }));
    // Drive an ApprovalRequested event into the panel, then keep the run pending
    // so the awaiting state is stable while we assert on the approve buttons.
    const run = vi.fn((_p: RunParams, handlers: RunHandlers) => {
      handlers.onEvent({ type: "ApprovalRequested", payload: { advisory_verdict: "approve", advisory_rationale: "ok" } });
      return new Promise<{ status: "finished"; session_id: string }>(() => {});
    });
    render(
      <IpcProvider client={{ run, approve } as unknown as IpcClient}>
        <RunPanel />
      </IpcProvider>,
    );
    fireEvent.change(screen.getByLabelText("initiative"), { target: { value: "X" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));

    fireEvent.click(await screen.findByRole("button", { name: /^reject$/i }));
    await waitFor(() => expect(approve).toHaveBeenCalledWith("reject", ""));
  });

  it("cancels a running session via run.cancel", async () => {
    const runCancel = vi.fn(async () => ({ ok: true }));
    const run = vi.fn((_p: RunParams, handlers: RunHandlers) => {
      handlers.onEvent({ type: "SessionStarted", payload: { session_id: "sx" } });
      return new Promise<{ status: "finished"; session_id: string }>(() => {});
    });
    render(
      <IpcProvider client={{ run, runCancel } as unknown as IpcClient}>
        <RunPanel />
      </IpcProvider>,
    );
    fireEvent.change(screen.getByLabelText("initiative"), { target: { value: "X" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));
    fireEvent.click(await screen.findByRole("button", { name: /^cancel$/i }));
    await waitFor(() => expect(runCancel).toHaveBeenCalledWith("sx"));
  });
});

describe("RunPanel stage timeline", () => {
  it("shows all pipeline stage labels when a run is in progress", async () => {
    const run = vi.fn((_p: RunParams, handlers: RunHandlers) => {
      handlers.onEvent({ type: "SessionStarted", payload: { session_id: "s" } });
      return new Promise<never>(() => {});
    });
    render(
      <IpcProvider client={{ run } as unknown as IpcClient}>
        <RunPanel />
      </IpcProvider>,
    );
    fireEvent.change(screen.getByLabelText("initiative"), { target: { value: "test" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));
    expect(await screen.findByText("Customer Research")).toBeInTheDocument();
    expect(screen.getByText("Final Verdict")).toBeInTheDocument();
  });

  it("marks a stage running on NodeProgress", async () => {
    let onEvent: ((e: IpcEvent) => void) | undefined;
    const run = vi.fn((_p: RunParams, handlers: RunHandlers) => {
      onEvent = handlers.onEvent;
      handlers.onEvent({ type: "SessionStarted", payload: { session_id: "s" } });
      return new Promise<never>(() => {});
    });
    render(
      <IpcProvider client={{ run } as unknown as IpcClient}>
        <RunPanel />
      </IpcProvider>,
    );
    fireEvent.change(screen.getByLabelText("initiative"), { target: { value: "test" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));
    await screen.findByText("Customer Research"); // wait for timeline to mount
    await act(async () => {
      onEvent?.({ type: "NodeProgress", payload: { node: "judge" } });
    });
    const item = screen.getByText("Judge").closest("[data-status]");
    expect(item).toHaveAttribute("data-status", "running");
  });

  it("renders the stage timeline for streamed events", async () => {
    const run = vi.fn((_p: RunParams, handlers: RunHandlers) => {
      handlers.onEvent({ type: "AnalystCompleted", payload: { node: "market", report: { analyst: "market", role: "M", findings: ["demand up"], signals: [], failed: false } } });
      return new Promise<{ status: "finished"; session_id: string }>(() => {});
    });
    render(
      <IpcProvider client={{ run } as unknown as IpcClient}>
        <RunPanel />
      </IpcProvider>,
    );
    fireEvent.change(screen.getByLabelText("initiative"), { target: { value: "X" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));
    expect(await screen.findByText("Market")).toBeInTheDocument();
    expect(screen.getByText("demand up")).toBeInTheDocument();
  });
});

describe("RunPanel running callback", () => {
  it("reports running=true while a run is in flight and false once it settles", async () => {
    const events: boolean[] = [];
    let resolveRun!: (value: { status: "finished"; session_id: string }) => void;
    const run = vi.fn(
      () =>
        new Promise<{ status: "finished"; session_id: string }>((resolve) => {
          resolveRun = resolve;
        }),
    );
    render(
      <IpcProvider client={{ run } as unknown as IpcClient}>
        <RunPanel onRunningChange={(running) => events.push(running)} />
      </IpcProvider>,
    );
    fireEvent.change(screen.getByLabelText("initiative"), { target: { value: "X" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));
    await waitFor(() => expect(events).toContain(true));
    await act(async () => {
      resolveRun({ status: "finished", session_id: "s" });
    });
    await waitFor(() => expect(events[events.length - 1]).toBe(false));
  });
});
