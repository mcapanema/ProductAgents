import type { ConnectorHealth, ConnectorList, ConnectorSync } from "../ipc/types";

export interface ConnectorRow {
  name: string;
  health: "ok" | "error" | "unknown";
  detail: string;
  written: number | null;
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
    };
  });
}
