import { describe, it, expect } from "vitest";
import { defaultDiffPair, versionLabel } from "./promptView";
import type { PromptSummary } from "../ipc/types";

describe("versionLabel", () => {
  it("labels version 0 as the bundled default", () => {
    expect(versionLabel(0, 0)).toBe("v0 · default");
    expect(versionLabel(0, 2)).toBe("v0 · default");
  });

  it("labels the active override version", () => {
    expect(versionLabel(2, 2)).toBe("v2 · active");
  });

  it("labels a non-active override plainly", () => {
    expect(versionLabel(1, 2)).toBe("v1");
  });
});

describe("defaultDiffPair", () => {
  it("returns null when only the bundled default exists", () => {
    const summary: PromptSummary = { name: "judge", versions: [0], active: 0 };
    expect(defaultDiffPair(summary)).toBeNull();
  });

  it("pairs the bundled default with the active version", () => {
    const summary: PromptSummary = { name: "strategist", versions: [0, 1, 2], active: 2 };
    expect(defaultDiffPair(summary)).toEqual([0, 2]);
  });
});
