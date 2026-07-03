import type { ConnectorConfigEntry, ConnectorHealth, ConnectorList, ConnectorSync } from "../ipc/types";

export type ConnectorStatusKind = "connected" | "error" | "unchecked" | "off";

export interface ConnectorStatus {
  kind: ConnectorStatusKind;
  label: string;
  detail: string;
}

/** A connector counts as enabled when it has a saved config block that isn't
 * explicitly disabled. An empty block means "never configured" → available. */
export function isEnabled(entry: ConnectorConfigEntry): boolean {
  return Object.keys(entry.config).length > 0 && entry.config.enabled !== false;
}

export function splitEntries(entries: ConnectorConfigEntry[]): {
  enabled: ConnectorConfigEntry[];
  available: ConnectorConfigEntry[];
} {
  return {
    enabled: entries.filter(isEnabled),
    available: entries.filter((e) => !isEnabled(e)),
  };
}

/** Status shown in the nav dot and the detail badge. Health is only known
 * after a `connectors.health` call this session — "unchecked" until then. */
export function connectorStatus(
  entry: ConnectorConfigEntry,
  health: ConnectorHealth | null,
): ConnectorStatus {
  if (!isEnabled(entry)) return { kind: "off", label: "Not connected", detail: "" };
  const status = health?.statuses[entry.connector];
  if (!status) return { kind: "unchecked", label: "Not checked", detail: "" };
  return status.ok
    ? { kind: "connected", label: "Connected", detail: status.detail }
    : { kind: "error", label: "Error", detail: status.detail };
}

export function syncSummary(name: string, sync: ConnectorSync | null): string | null {
  const result = sync?.results.find((r) => r.connector === name);
  if (!result) return null;
  return result.ok ? `${result.written} records written` : `Sync failed: ${result.error}`;
}

export function lastSynced(name: string, list: ConnectorList | null): string | null {
  return list?.last_synced?.[name] ?? null;
}

/** Overlay a (possibly single-connector) health report onto the previous one,
 * so checking one connector never wipes another's badge. */
export function mergeHealth(
  prev: ConnectorHealth | null,
  next: ConnectorHealth,
): ConnectorHealth {
  return { statuses: { ...prev?.statuses, ...next.statuses }, problems: next.problems };
}

/** Same overlay for sync reports: replace results for the connectors in `next`,
 * keep the rest. */
export function mergeSync(prev: ConnectorSync | null, next: ConnectorSync): ConnectorSync {
  const updated = new Set(next.results.map((r) => r.connector));
  return {
    results: [
      ...(prev?.results ?? []).filter((r) => !updated.has(r.connector)),
      ...next.results,
    ],
    problems: next.problems,
  };
}
