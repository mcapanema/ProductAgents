import type { PromptSummary } from "../ipc/types";

/** Human label for a prompt version: v0 is the bundled default; the highest is active. */
export function versionLabel(version: number, active: number): string {
  if (version === 0) return "v0 · default";
  if (version === active) return `v${version} · active`;
  return `v${version}`;
}

/** The default diff to show: bundled default vs active, or null if nothing overrides it. */
export function defaultDiffPair(summary: PromptSummary): [number, number] | null {
  return summary.active === 0 ? null : [0, summary.active];
}
