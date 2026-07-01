import { beforeEach, describe, expect, it } from "vitest";
import { theme as antdTheme } from "antd";
import { buildAntdTheme } from "./theme";

function setVar(name: string, value: string) {
  document.documentElement.style.setProperty(name, value);
}

describe("buildAntdTheme", () => {
  beforeEach(() => {
    setVar("--accent", "#4f5b9a");
    setVar("--surface-raised", "#ffffff");
    setVar("--bg-primary", "#f4f1ea");
    setVar("--text-primary", "#14171c");
    setVar("--text-secondary", "#3a4048");
    setVar("--border-default", "#7f8791");
    setVar("--text-error", "#8a1f1f");
    setVar("--text-success", "#1f6e40");
    setVar("--text-warning", "#7a5200");
    setVar("--text-info", "#1f4e8a");
    setVar("--font-sans", '"IBM Plex Sans", sans-serif');
    setVar("--radius-field", "4px");
    setVar("--control-md", "36px");
  });

  it("maps color/font/size tokens onto AntD seed tokens", () => {
    const cfg = buildAntdTheme("light", "comfortable");
    expect(cfg.token?.colorPrimary).toBe("#4f5b9a");
    expect(cfg.token?.colorBgContainer).toBe("#ffffff");
    expect(cfg.token?.colorError).toBe("#8a1f1f");
    expect(cfg.token?.colorSuccess).toBe("#1f6e40");
    expect(cfg.token?.fontFamily).toBe('"IBM Plex Sans", sans-serif');
    expect(cfg.token?.borderRadius).toBe(4);
    expect(cfg.token?.controlHeight).toBe(36);
  });

  it("selects the default algorithm in light mode", () => {
    const cfg = buildAntdTheme("light", "comfortable");
    expect(cfg.algorithm).toEqual([antdTheme.defaultAlgorithm]);
  });

  it("selects the dark algorithm in dark mode", () => {
    const cfg = buildAntdTheme("dark", "comfortable");
    expect(cfg.algorithm).toEqual([antdTheme.darkAlgorithm]);
  });

  it("appends the compact algorithm in compact density", () => {
    const cfg = buildAntdTheme("light", "compact");
    expect(cfg.algorithm).toEqual([antdTheme.defaultAlgorithm, antdTheme.compactAlgorithm]);
  });

  it("falls back to sane defaults when a size token is missing or unparsable", () => {
    setVar("--radius-field", "");
    setVar("--control-md", "not-a-number");
    const cfg = buildAntdTheme("light", "comfortable");
    expect(cfg.token?.borderRadius).toBe(4);
    expect(cfg.token?.controlHeight).toBe(36);
  });
});
