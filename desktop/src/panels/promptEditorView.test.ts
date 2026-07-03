import { describe, it, expect } from "vitest";
import { extractVariables, lineDiff, isDirty } from "./promptEditorView";

describe("extractVariables", () => {
  it("finds $name and ${name} tokens, de-duplicated, in order", () => {
    expect(extractVariables("$persona argues $initiative.\nFindings: ${reports} and $persona"))
      .toEqual(["persona", "initiative", "reports"]);
  });
  it("returns [] when there are no variables", () => {
    expect(extractVariables("plain prompt")).toEqual([]);
  });
});

describe("lineDiff", () => {
  it("labels unchanged, added and removed lines", () => {
    expect(lineDiff("a\nb\nc", "a\nx\nc")).toEqual([
      { type: "same", text: "a" },
      { type: "del", text: "b" },
      { type: "add", text: "x" },
      { type: "same", text: "c" },
    ]);
  });
  it("handles pure insertion", () => {
    expect(lineDiff("a\nc", "a\nb\nc")).toEqual([
      { type: "same", text: "a" },
      { type: "add", text: "b" },
      { type: "same", text: "c" },
    ]);
  });
  it("identical text is all 'same'", () => {
    expect(lineDiff("x\ny", "x\ny").every((l) => l.type === "same")).toBe(true);
  });
});

describe("isDirty", () => {
  it("is true only when the draft differs from the original", () => {
    expect(isDirty("a", "a")).toBe(false);
    expect(isDirty("a ", "a")).toBe(true);
  });
});
