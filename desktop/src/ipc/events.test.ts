import { describe, it, expect } from "vitest";
import { STAGE_DEFS, nodeToStage, emptyDetail } from "./events";

describe("stage model", () => {
  it("orders the 12 pipeline stages", () => {
    expect(STAGE_DEFS.map((d) => d.key)).toEqual([
      "customer_research", "product_analytics", "market", "business", "technical",
      "recall", "debate", "strategist", "judge", "risk", "governance", "final",
    ]);
  });

  it("maps analyst node names to their own stage key", () => {
    expect(nodeToStage("market")).toBe("market");
    expect(nodeToStage("customer_research")).toBe("customer_research");
  });

  it("aliases human_approval to the final stage", () => {
    expect(nodeToStage("human_approval")).toBe("final");
  });

  it("returns undefined for an unknown node", () => {
    expect(nodeToStage("nope")).toBeUndefined();
  });

  it("starts every stage with an empty detail", () => {
    expect(emptyDetail()).toEqual({ kind: "none" });
  });
});
