import { describe, it, expect } from "vitest";
import { nodeKind, KIND_META } from "./workflowNodeKinds";

describe("nodeKind", () => {
  it("maps each of the five analysts to its own kind", () => {
    expect(nodeKind("customer_research")).toBe("analyst-customer");
    expect(nodeKind("product_analytics")).toBe("analyst-analytics");
    expect(nodeKind("market")).toBe("analyst-market");
    expect(nodeKind("business")).toBe("analyst-business");
    expect(nodeKind("technical")).toBe("analyst-technical");
  });

  it("maps the spine, memory, approval and terminals", () => {
    expect(nodeKind("debate")).toBe("debate");
    expect(nodeKind("strategist")).toBe("strategist");
    expect(nodeKind("judge")).toBe("judge");
    expect(nodeKind("risk")).toBe("risk");
    expect(nodeKind("governance")).toBe("governance");
    expect(nodeKind("recall")).toBe("memory");
    expect(nodeKind("human_approval")).toBe("approval");
    expect(nodeKind("__start__")).toBe("terminal");
    expect(nodeKind("__end__")).toBe("terminal");
  });

  it("falls back to spine for unknown nodes", () => {
    expect(nodeKind("some_future_node")).toBe("spine");
  });

  it("gives every kind a distinct analyst hue token and metadata", () => {
    const analystTokens = new Set(
      (["analyst-customer","analyst-analytics","analyst-market","analyst-business","analyst-technical"] as const)
        .map((k) => KIND_META[k].colorToken),
    );
    expect(analystTokens.size).toBe(5); // five distinct hues
    for (const meta of Object.values(KIND_META)) {
      expect(meta.label.length).toBeGreaterThan(0);
      expect(meta.description.length).toBeGreaterThan(0);
      expect(meta.colorToken.startsWith("--")).toBe(true);
    }
  });
});
