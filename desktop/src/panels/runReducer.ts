import type { IpcEvent, RunResult } from "../ipc/types";

export interface RunState {
  status: "idle" | "running" | "finished" | "failed" | "cancelled" | "error";
  events: IpcEvent[];
  awaiting: boolean;
  advisory?: { verdict: string; rationale: string };
  sessionId?: string;
  cancelling?: boolean;
  error?: string;
}

export const initialRunState: RunState = { status: "idle", events: [], awaiting: false };

export type RunAction =
  | { kind: "start" }
  | { kind: "event"; event: IpcEvent }
  | { kind: "approved" }
  | { kind: "cancel" }
  | { kind: "done"; result: RunResult }
  | { kind: "error"; message: string };

export function runReducer(state: RunState, action: RunAction): RunState {
  switch (action.kind) {
    case "start":
      return { status: "running", events: [], awaiting: false, cancelling: false };
    case "event": {
      const next = { ...state, events: [...state.events, action.event] };
      const sid = action.event.payload.session_id;
      if (typeof sid === "string") next.sessionId = sid;
      if (action.event.type === "ApprovalRequested") {
        next.awaiting = true;
        next.advisory = {
          verdict: String(action.event.payload.advisory_verdict ?? ""),
          rationale: String(action.event.payload.advisory_rationale ?? ""),
        };
      } else if (action.event.type === "FinalVerdict") {
        next.awaiting = false;
      }
      return next;
    }
    case "approved":
      return { ...state, awaiting: false };
    case "cancel":
      return { ...state, cancelling: true };
    case "done":
      return { ...state, status: action.result.status, sessionId: action.result.session_id, awaiting: false, cancelling: false };
    case "error":
      return { ...state, status: "error", error: action.message, awaiting: false, cancelling: false };
  }
}
