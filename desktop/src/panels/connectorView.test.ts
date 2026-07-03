import { describe, it, expect } from "vitest";
import {
  connectorRows,
  connectorStatus,
  isEnabled,
  lastSynced,
  splitEntries,
  syncSummary,
} from "./connectorView";
import type { ConnectorConfigEntry, ConnectorHealth, ConnectorList, ConnectorSync } from "../ipc/types";

const list: ConnectorList = {
  connectors: [{ name: "github" }, { name: "jira" }],
  problems: [],
};

describe("connectorRows", () => {
  it("marks connectors unknown when no health or sync is loaded yet", () => {
    const rows = connectorRows(list, null, null);
    expect(rows).toEqual([
      { name: "github", health: "unknown", detail: "", written: null, synced: null, error: null, lastSynced: null },
      { name: "jira", health: "unknown", detail: "", written: null, synced: null, error: null, lastSynced: null },
    ]);
  });

  it("marks synced=error and captures error message for a failed sync result", () => {
    const sync: ConnectorSync = {
      results: [{ connector: "github", written: 0, ok: false, error: "401 unauthorized" }],
      problems: [],
    };
    const rows = connectorRows(list, null, sync);
    expect(rows[0]).toMatchObject({ synced: "error", error: "401 unauthorized", written: 0 });
  });

  it("merges health status and last sync counts per connector", () => {
    const health: ConnectorHealth = {
      statuses: {
        github: { ok: true, detail: "reachable" },
        jira: { ok: false, detail: "401 unauthorized" },
      },
      problems: [],
    };
    const sync: ConnectorSync = {
      results: [{ connector: "github", written: 7, ok: true, error: null }],
      problems: [],
    };
    const rows = connectorRows(list, health, sync);
    expect(rows[0]).toEqual({
      name: "github",
      health: "ok",
      detail: "reachable",
      written: 7,
      synced: "ok",
      error: null,
      lastSynced: null,
    });
    expect(rows[1]).toEqual({
      name: "jira",
      health: "error",
      detail: "401 unauthorized",
      written: null,
      synced: null,
      error: null,
      lastSynced: null,
    });
  });

  it("carries the last-sync timestamp onto the row", () => {
    const list: ConnectorList = {
      connectors: [{ name: "github" }],
      problems: [],
      last_synced: { github: "2026-06-29T10:00:00+00:00" },
    };
    const rows = connectorRows(list, null, null);
    expect(rows[0].lastSynced).toBe("2026-06-29T10:00:00+00:00");
  });
});

function entry(connector: string, config: Record<string, unknown>): ConnectorConfigEntry {
  return { connector, installed: true, config, schema: null, problems: [] };
}

const explicitOn = entry("github", { owner: "acme", enabled: true });
const implicitOn = entry("jira", { url: "https://x.atlassian.net" });
const explicitOff = entry("linear", { enabled: false });
const unconfigured = entry("slack", {});

describe("splitEntries", () => {
  it("treats a non-empty, not-disabled config block as enabled", () => {
    expect(isEnabled(explicitOn)).toBe(true);
    expect(isEnabled(implicitOn)).toBe(true);
    expect(isEnabled(explicitOff)).toBe(false);
    expect(isEnabled(unconfigured)).toBe(false);
  });

  it("splits entries into enabled and available, preserving order", () => {
    const { enabled, available } = splitEntries([explicitOn, implicitOn, explicitOff, unconfigured]);
    expect(enabled.map((e) => e.connector)).toEqual(["github", "jira"]);
    expect(available.map((e) => e.connector)).toEqual(["linear", "slack"]);
  });
});

describe("connectorStatus", () => {
  const health: ConnectorHealth = {
    statuses: {
      github: { ok: true, detail: "reachable" },
      jira: { ok: false, detail: "401 unauthorized" },
    },
    problems: [],
  };

  it("is off for disabled or unconfigured connectors", () => {
    expect(connectorStatus(unconfigured, health)).toEqual({ kind: "off", label: "Not connected", detail: "" });
    expect(connectorStatus(explicitOff, null).kind).toBe("off");
  });

  it("is unchecked for an enabled connector before any health check", () => {
    expect(connectorStatus(explicitOn, null)).toEqual({ kind: "unchecked", label: "Not checked", detail: "" });
  });

  it("maps a health result to connected or error with its detail", () => {
    expect(connectorStatus(explicitOn, health)).toEqual({ kind: "connected", label: "Connected", detail: "reachable" });
    expect(connectorStatus(implicitOn, health)).toEqual({ kind: "error", label: "Error", detail: "401 unauthorized" });
  });
});

describe("syncSummary and lastSynced", () => {
  const sync: ConnectorSync = {
    results: [
      { connector: "github", written: 7, ok: true, error: null },
      { connector: "jira", written: 0, ok: false, error: "boom" },
    ],
    problems: [],
  };

  it("summarizes a connector's sync result, null when absent", () => {
    expect(syncSummary("github", sync)).toBe("7 records written");
    expect(syncSummary("jira", sync)).toBe("Sync failed: boom");
    expect(syncSummary("slack", sync)).toBeNull();
    expect(syncSummary("github", null)).toBeNull();
  });

  it("reads a connector's last-synced timestamp from the list payload", () => {
    const list: ConnectorList = {
      connectors: [{ name: "github" }],
      problems: [],
      last_synced: { github: "2026-06-29T10:00:00+00:00" },
    };
    expect(lastSynced("github", list)).toBe("2026-06-29T10:00:00+00:00");
    expect(lastSynced("jira", list)).toBeNull();
    expect(lastSynced("github", null)).toBeNull();
  });
});
