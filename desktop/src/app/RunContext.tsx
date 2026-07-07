import { createContext, useContext, useReducer } from "react";
import type { ReactNode } from "react";
import { useIpc } from "./IpcProvider";
import { runReducer, initialRunState } from "../panels/runReducer";
import type { RunState } from "../panels/runReducer";
import type { RunParams } from "../ipc/types";

interface RunApi {
  state: RunState;
  start: (params: RunParams) => Promise<void>;
  decide: (verdict: string) => Promise<void>;
  cancel: () => Promise<void>;
}

const RunContext = createContext<RunApi | null>(null);

export function useRun(): RunApi {
  const ctx = useContext(RunContext);
  if (!ctx) throw new Error("useRun must be used within a RunProvider");
  return ctx;
}

/**
 * Owns the decision-run reducer and its actions, mounted above the panel switch
 * so a run's streamed timeline and running state survive `RunPanel` unmounting
 * on navigation. The `ipc.run` promise and its `onEvent`/terminal dispatch land
 * here, not in the panel, so they keep updating after the panel is gone.
 */
export function RunProvider({ children }: { children: ReactNode }) {
  const ipc = useIpc();
  const [state, dispatch] = useReducer(runReducer, initialRunState);

  async function start(params: RunParams) {
    if (!ipc) return;
    dispatch({ kind: "start" });
    try {
      const result = await ipc.run(params, {
        onEvent: (event) => dispatch({ kind: "event", event }),
      });
      dispatch({ kind: "done", result });
    } catch (err) {
      dispatch({ kind: "error", message: err instanceof Error ? err.message : String(err) });
    }
  }

  async function decide(verdict: string) {
    if (!ipc) return;
    dispatch({ kind: "approved" });
    try {
      await ipc.approve(verdict, "");
    } catch {
      // the run will surface failure via its terminal result/error
    }
  }

  async function cancel() {
    if (!ipc || !state.sessionId) return;
    dispatch({ kind: "cancel" });
    try {
      await ipc.runCancel(state.sessionId);
    } catch {
      // terminal result/error will surface the outcome
    }
  }

  return <RunContext.Provider value={{ state, start, decide, cancel }}>{children}</RunContext.Provider>;
}
