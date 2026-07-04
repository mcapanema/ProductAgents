// desktop/src/ui/ThemeShell.tsx
import { useLayoutEffect, useState } from "react";
import type { ReactNode } from "react";
import { App, ConfigProvider } from "antd";
import type { ThemeConfig } from "antd";
import { buildAntdTheme } from "./theme";
import type { Density, Theme } from "./theme";

/**
 * Owns the data-theme/data-density DOM attributes AND the antd ConfigProvider
 * theme config in one component so both useLayoutEffects run in the same
 * commit, in declaration order — the attribute write always lands before
 * buildAntdTheme re-reads the resolved CSS custom properties. Fixes the race
 * documented in design/docs/antd-pilot-evaluation.md (stale colors for one
 * commit on the first light<->dark toggle).
 *
 * Also wraps children in antd's `<App>` so the static-style `Modal.confirm`/
 * `message`/`notification` APIs, called via `App.useApp()`, render inside
 * this theme's ConfigProvider context — otherwise those calls mount outside
 * the React tree entirely and always render with antd's default look,
 * regardless of this app's design-system tokens.
 */
export function ThemeShell({
  theme,
  density,
  children,
}: {
  theme: Theme;
  density: Density;
  children: ReactNode;
}) {
  useLayoutEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);
  useLayoutEffect(() => {
    document.documentElement.setAttribute("data-density", density);
  }, [density]);

  const [config, setConfig] = useState<ThemeConfig>(() => buildAntdTheme(theme, density));
  useLayoutEffect(() => {
    setConfig(buildAntdTheme(theme, density));
  }, [theme, density]);

  return (
    <ConfigProvider theme={config}>
      <App>{children}</App>
    </ConfigProvider>
  );
}
