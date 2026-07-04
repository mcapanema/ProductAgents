import type { IpcEvent, NodeStatus } from "../ipc/types";

interface StatusStyle {
  border: string; // var() ref
  text: string; // var() ref
  pulse: boolean;
}

const STYLE: Record<NodeStatus, StatusStyle> = {
  idle: { border: "var(--ai-node-border)", text: "var(--text-primary)", pulse: false },
  waiting: { border: "var(--ai-waiting)", text: "var(--text-tertiary)", pulse: false },
  running: { border: "var(--ai-running)", text: "var(--ai-running-text)", pulse: true },
  done: { border: "var(--ai-done)", text: "var(--ai-done-text)", pulse: false },
  degraded: { border: "var(--ai-degraded)", text: "var(--ai-degraded-text)", pulse: false },
  failed: { border: "var(--ai-failed)", text: "var(--ai-failed-text)", pulse: false },
  "awaiting-human": { border: "var(--ai-awaiting-human)", text: "var(--text-primary)", pulse: true },
  cancelled: { border: "var(--ai-cancelled)", text: "var(--text-tertiary)", pulse: false },
};

export function statusStyle(status: NodeStatus): StatusStyle {
  return STYLE[status];
}

/**
 * Fold a run's event stream into a per-node status map. The Workflows config
 * view passes `[]` (every node renders "idle"); the live-run view (future,
 * separate plan) passes the accumulated events from `runReducer`.
 * ponytail: last-writer-wins per node — the pipeline visits each node once
 * except the judge→strategist retry, where "running" correctly re-supersedes.
 */
export function deriveNodeStatuses(events: IpcEvent[]): Record<string, NodeStatus> {
  const out: Record<string, NodeStatus> = {};
  for (const e of events) {
    if (e.type === "ApprovalRequested") {
      out.human_approval = "awaiting-human";
      continue;
    }
    const node = typeof e.payload.node === "string" ? e.payload.node : null;
    if (!node) continue;
    if (e.type === "NodeProgress") out[node] = "running";
    else if (e.type === "AnalystCompleted") out[node] = "done";
    else if (e.type === "NodeFailed") out[node] = "degraded";
    else if (e.type === "SessionFailed") out[node] = "failed";
  }
  return out;
}
