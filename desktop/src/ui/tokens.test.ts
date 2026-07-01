import { beforeEach, describe, expect, it } from "vitest";
import { RUNTIME_TOKENS, readToken, readTokens, tokenVar } from "./tokens";

describe("tokenVar", () => {
  it("wraps a token name in a var() reference", () => {
    expect(tokenVar("--accent")).toBe("var(--accent)");
  });
});

describe("readToken / readTokens", () => {
  beforeEach(() => {
    document.documentElement.style.setProperty("--accent", "#4f5b9a");
    document.documentElement.style.setProperty("--text-primary", "#14171c");
  });

  it("reads a single resolved token value from :root", () => {
    expect(readToken("--accent")).toBe("#4f5b9a");
  });

  it("returns empty string for an unset token", () => {
    expect(readToken("--nope-not-a-token")).toBe("");
  });

  it("batch-reads several tokens in one pass", () => {
    const v = readTokens(["--accent", "--text-primary"] as const);
    expect(v["--accent"]).toBe("#4f5b9a");
    expect(v["--text-primary"]).toBe("#14171c");
  });

  it("RUNTIME_TOKENS enumerates the tokens the theme adapter seeds", () => {
    expect(RUNTIME_TOKENS).toContain("--accent");
    expect(RUNTIME_TOKENS).toContain("--control-md");
  });
});
