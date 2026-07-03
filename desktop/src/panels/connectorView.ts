import type { ConnectorConfigEntry, ConnectorHealth, ConnectorList, ConnectorSync } from "../ipc/types";

export interface ConnectorRow {
  name: string;
  health: "ok" | "error" | "unknown";
  detail: string;
  written: number | null;
  synced: "ok" | "error" | null;
  error: string | null;
  lastSynced: string | null;
}

/** Merge the three connector views into one row per configured connector. */
export function connectorRows(
  list: ConnectorList,
  health: ConnectorHealth | null,
  sync: ConnectorSync | null,
): ConnectorRow[] {
  return list.connectors.map((c) => {
    const status = health?.statuses[c.name];
    const result = sync?.results.find((r) => r.connector === c.name);
    return {
      name: c.name,
      health: status ? (status.ok ? "ok" : "error") : "unknown",
      detail: status?.detail ?? "",
      written: result ? result.written : null,
      synced: result ? (result.ok ? "ok" : "error") : null,
      error: result ? result.error : null,
      lastSynced: list.last_synced?.[c.name] ?? null,
    };
  });
}

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
