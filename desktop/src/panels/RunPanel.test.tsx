import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { RunPanel } from "./RunPanel";
import { IpcProvider } from "../app/IpcProvider";
import type { IpcClient } from "../ipc/client";
import type { RunHandlers, RunParams } from "../ipc/types";

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
});
