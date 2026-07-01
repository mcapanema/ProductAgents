import { useCallback, useEffect, useState } from "react";
import type { Theme, ThemePref } from "./theme";
import { readStoredPref, readSystemTheme, writeStoredPref } from "./theme";

/**
 * Owns the user's theme *preference* (persisted to localStorage) and resolves
 * it into the concrete Theme to apply. When the preference is "system", the OS
 * `prefers-color-scheme` media query is tracked live so a mid-session OS theme
 * switch re-renders the app.
 */
export function useThemePreference(): {
  pref: ThemePref;
  setPref: (pref: ThemePref) => void;
  resolved: Theme;
} {
  const [pref, setPrefState] = useState<ThemePref>(readStoredPref);
  const [systemTheme, setSystemTheme] = useState<Theme>(readSystemTheme);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => setSystemTheme(mq.matches ? "dark" : "light");
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const setPref = useCallback((next: ThemePref) => {
    setPrefState(next);
    writeStoredPref(next);
  }, []);

  const resolved: Theme = pref === "system" ? systemTheme : pref;
  return { pref, setPref, resolved };
}
