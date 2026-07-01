import { theme as antdTheme } from "antd";
import type { ThemeConfig } from "antd";
import type { Density, Theme } from "../sg";

const TOKEN_VARS = [
  "--accent",
  "--surface-raised",
  "--bg-primary",
  "--text-primary",
  "--text-secondary",
  "--border-default",
  "--text-error",
  "--text-success",
  "--text-warning",
  "--text-info",
  "--font-sans",
  "--radius-field",
  "--control-md",
] as const;

type TokenVar = (typeof TOKEN_VARS)[number];

function readVars(): Record<TokenVar, string> {
  const cs = getComputedStyle(document.documentElement);
  const out = {} as Record<TokenVar, string>;
  for (const name of TOKEN_VARS) out[name] = cs.getPropertyValue(name).trim();
  return out;
}

function toPx(value: string, fallback: number): number {
  const n = parseFloat(value);
  return Number.isFinite(n) ? n : fallback;
}

/**
 * Maps the ProductAgents "Instrument" design tokens (design/tokens/*.css,
 * already applied to <html> via data-theme/data-density — see App.tsx) onto
 * Ant Design's ConfigProvider seed tokens, so the pilot components inherit
 * the real system instead of AntD's default blue theme. This keeps the
 * token CSS files as the single source of truth — no color/size is
 * hardcoded here.
 */
export function buildAntdTheme(mode: Theme, density: Density): ThemeConfig {
  const v = readVars();
  return {
    algorithm: [
      mode === "dark" ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
      ...(density === "compact" ? [antdTheme.compactAlgorithm] : []),
    ],
    cssVar: { prefix: "antd-pilot" },
    hashed: false,
    token: {
      colorPrimary: v["--accent"],
      colorBgContainer: v["--surface-raised"],
      colorBgLayout: v["--bg-primary"],
      colorText: v["--text-primary"],
      colorTextSecondary: v["--text-secondary"],
      colorBorder: v["--border-default"],
      colorError: v["--text-error"],
      colorSuccess: v["--text-success"],
      colorWarning: v["--text-warning"],
      colorInfo: v["--text-info"],
      fontFamily: v["--font-sans"],
      borderRadius: toPx(v["--radius-field"], 4),
      controlHeight: toPx(v["--control-md"], 36),
    },
  };
}
