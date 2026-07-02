import { describe, expect, it } from "vitest";
import {
  CREATE_OPTION,
  activeWorkspaceName,
  filterEntries,
  searchEntries,
  validWorkspaceName,
  workspaceOptions,
} from "./topBarView";
import type { WorkspaceInfo } from "../ipc/types";

const ws = (name: string, active = false) =>
  ({ name, active }) as WorkspaceInfo;

describe("searchEntries", () => {
  it("flattens decisions, sessions and workflows with target views", () => {
    const entries = searchEntries(
      [{ id: "d1", title: "Dark mode", recommendation: "go", confidence: 0.8, created_at: "t" }],
      [{ id: "s1", workflow: "evaluate_initiative", status: "finished", created_at: "t" }],
      [{ name: "evaluate_initiative", title: "Evaluate Initiative", description: "" }],
    );
    expect(entries.map((e) => e.view)).toEqual(["decisions", "sessions", "workflows"]);
    expect(entries[0].label).toBe("Dark mode");
  });
});

describe("filterEntries", () => {
  const entries = searchEntries(
    [{ id: "d1", title: "Dark mode", recommendation: "go", confidence: 0.8, created_at: "t" }],
    [],
    [{ name: "evaluate_initiative", title: "Evaluate Initiative", description: "" }],
  );

  it("matches case-insensitively on the label", () => {
    expect(filterEntries(entries, "dark").map((e) => e.key)).toEqual(["decision:d1"]);
  });

  it("returns nothing for a blank query", () => {
    expect(filterEntries(entries, "  ")).toEqual([]);
  });
});

describe("workspaceOptions / activeWorkspaceName", () => {
  it("lists workspaces then the create action", () => {
    const opts = workspaceOptions([ws("default", true), ws("acme")]);
    expect(opts.map((o) => o.value)).toEqual(["default", "acme", CREATE_OPTION]);
  });

  it("finds the active workspace, defaulting to 'default'", () => {
    expect(activeWorkspaceName([ws("a"), ws("b", true)])).toBe("b");
    expect(activeWorkspaceName([])).toBe("default");
  });
});

describe("validWorkspaceName", () => {
  it("accepts directory-safe names and rejects the rest", () => {
    expect(validWorkspaceName("team-x")).toBe(true);
    expect(validWorkspaceName("Acme_2.0")).toBe(true);
    expect(validWorkspaceName("")).toBe(false);
    expect(validWorkspaceName(".hidden")).toBe(false);
    expect(validWorkspaceName("a/b")).toBe(false);
    expect(validWorkspaceName("a b")).toBe(false);
  });
});
