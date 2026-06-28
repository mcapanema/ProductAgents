import type { IpcEvent, RunResult } from "../ipc/types";

export interface RunState {
  status: "idle" | "running" | "finished" | "failed" | "error";
  events: IpcEvent[];
  sessionId?: string;
  error?: string;
}

export const initialRunState: RunState = { status: "idle", events: [] };

export type RunAction =
  | { kind: "start" }
  | { kind: "event"; event: IpcEvent }
  | { kind: "done"; result: RunResult }
  | { kind: "error"; message: string };

export function runReducer(state: RunState, action: RunAction): RunState {
  switch (action.kind) {
    case "start":
      return { status: "running", events: [] };
    case "event":
      return { ...state, events: [...state.events, action.event] };
    case "done":
      return { ...state, status: action.result.status, sessionId: action.result.session_id };
    case "error":
      return { ...state, status: "error", error: action.message };
  }
}
