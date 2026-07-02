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

/** A user's theme *preference*: the two concrete themes plus "follow the OS". */
export type ThemePref = Theme | "system";

/** localStorage key for the persisted preference (cf. "pa-sidebar-collapsed"). */
export const THEME_STORAGE_KEY = "pa-theme";

const COLOR_SCHEME_QUERY = "(prefers-color-scheme: dark)";

/** The concrete theme the OS is currently asking for. */
export function readSystemTheme(): Theme {
  return window.matchMedia(COLOR_SCHEME_QUERY).matches ? "dark" : "light";
}

/** Collapse a preference into the concrete theme to actually apply. */
export function resolveTheme(pref: ThemePref): Theme {
  return pref === "system" ? readSystemTheme() : pref;
}

/** Read the persisted preference, defaulting to "light" when absent/invalid. */
export function readStoredPref(): ThemePref {
  const v = localStorage.getItem(THEME_STORAGE_KEY);
  return v === "light" || v === "dark" || v === "system" ? v : "light";
}

/** Persist the preference. */
export function writeStoredPref(pref: ThemePref): void {
  localStorage.setItem(THEME_STORAGE_KEY, pref);
}
