import type {
  DecisionSummary,
  SessionSummary,
  WorkflowSummary,
  WorkspaceInfo,
} from "../ipc/types";
import type { View } from "./Sidebar";

export interface SearchEntry {
  key: string;
  label: string;
  kind: "decision" | "session" | "workflow";
  view: View;
}

/** Flatten the searchable corpora into one entry list.
 * ponytail: search navigates to the owning panel, not the specific record —
 * deep-linking needs lifted selection state in each panel; add when asked. */
export function searchEntries(
  decisions: DecisionSummary[],
  sessions: SessionSummary[],
  workflows: WorkflowSummary[],
): SearchEntry[] {
  return [
    ...decisions.map((d) => ({
      key: `decision:${d.id}`,
      label: d.title,
      kind: "decision" as const,
      view: "decisions" as const,
    })),
    ...sessions.map((s) => ({
      key: `session:${s.id}`,
      label: `${s.workflow} · ${s.id}`,
      kind: "session" as const,
      view: "sessions" as const,
    })),
    ...workflows.map((w) => ({
      key: `workflow:${w.name}`,
      label: w.title,
      kind: "workflow" as const,
      view: "workflows" as const,
    })),
  ];
}

export function filterEntries(
  entries: SearchEntry[],
  query: string,
): SearchEntry[] {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  return entries.filter((e) => e.label.toLowerCase().includes(q)).slice(0, 12);
}

export const CREATE_OPTION = "__create__";

/** Options for the workspace Select: one per workspace + the create action. */
export function workspaceOptions(
  workspaces: WorkspaceInfo[],
): { value: string; label: string }[] {
  return [
    ...workspaces.map((w) => ({ value: w.name, label: w.name })),
    { value: CREATE_OPTION, label: "＋ New workspace…" },
  ];
}

export function activeWorkspaceName(workspaces: WorkspaceInfo[]): string {
  return workspaces.find((w) => w.active)?.name ?? "default";
}

/** Directory-safe workspace name — mirrors the backend's _NAME_RE. */
export function validWorkspaceName(name: string): boolean {
  return /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(name);
}
