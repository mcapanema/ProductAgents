// desktop/src/ui/theme.ts
import { theme as antdTheme } from "antd";
import type { ThemeConfig } from "antd";
import { RUNTIME_TOKENS, readTokens } from "./tokens";

export type Theme = "light" | "dark";
export type Density = "comfortable" | "compact";

function toPx(value: string, fallback: number): number {
  const n = parseFloat(value);
  return Number.isFinite(n) ? n : fallback;
}

/**
 * Maps the ProductAgents "Instrument" design tokens (design/tokens/*.css,
 * re-exported via ui/tokens.css and applied to <html> via data-theme/
 * data-density — see ui/ThemeShell.tsx) onto Ant Design's ConfigProvider seed
 * tokens. Ported from the validated pilot at
 * design/styleguide/src/antd-pilot/theme.ts — the token CSS files remain the
 * single source of truth, nothing hardcoded here.
 */
export function buildAntdTheme(mode: Theme, density: Density): ThemeConfig {
  const v = readTokens(RUNTIME_TOKENS);
  return {
    algorithm: [
      mode === "dark" ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
      ...(density === "compact" ? [antdTheme.compactAlgorithm] : []),
    ],
    cssVar: { prefix: "antd-desktop" },
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
