import { describe, expect, it } from "vitest";
import { updateStatusLabel, type UpdateState } from "./updateView";

describe("updateStatusLabel", () => {
  it("is quiet when idle", () => {
    expect(updateStatusLabel({ kind: "idle" })).toBe("");
  });

  it("reports while checking", () => {
    expect(updateStatusLabel({ kind: "checking" })).toBe("Checking for updates…");
  });

  it("reports up to date", () => {
    expect(updateStatusLabel({ kind: "none" })).toBe("You're on the latest version.");
  });

  it("names the available version", () => {
    const s: UpdateState = { kind: "available", version: "1.2.0" };
    expect(updateStatusLabel(s)).toBe("Update available: 1.2.0");
  });

  it("reports installing", () => {
    expect(updateStatusLabel({ kind: "installing" })).toBe("Downloading and installing…");
  });

  it("surfaces errors", () => {
    const s: UpdateState = { kind: "error", message: "network down" };
    expect(updateStatusLabel(s)).toBe("Update check failed: network down");
  });
});
