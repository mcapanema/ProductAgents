import { describe, it, expect } from "vitest";
import { connectorRows } from "./connectorView";
import type { ConnectorHealth, ConnectorList, ConnectorSync } from "../ipc/types";

const list: ConnectorList = {
  connectors: [{ name: "github" }, { name: "jira" }],
  problems: [],
};

describe("connectorRows", () => {
  it("marks connectors unknown when no health or sync is loaded yet", () => {
    const rows = connectorRows(list, null, null);
    expect(rows).toEqual([
      { name: "github", health: "unknown", detail: "", written: null },
      { name: "jira", health: "unknown", detail: "", written: null },
    ]);
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
    });
    expect(rows[1]).toEqual({
      name: "jira",
      health: "error",
      detail: "401 unauthorized",
      written: null,
    });
  });
});
