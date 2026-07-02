import { useCallback, useEffect, useState } from "react";
import type { IpcClient } from "../ipc/client";
import type { Theme, ThemePref } from "./theme";
import { readStoredPref, readSystemTheme, writeStoredPref } from "./theme";

const PREFS: readonly ThemePref[] = ["light", "dark", "system"];

/**
 * Owns the user's theme *preference*. localStorage is the instant-boot cache
 * (no flash before IPC is ready); the workspace DB is the source of truth —
 * once `ipc` connects, the stored preference is read and wins. Changes write
 * both. Preferences never affect workflow execution.
 */
export function useThemePreference(ipc?: IpcClient | null): {
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

  useEffect(() => {
    if (!ipc) return;
    let active = true;
    ipc
      .preferencesGet()
      .then(({ theme }) => {
        if (!active || !theme) return;
        if ((PREFS as readonly string[]).includes(theme)) {
          setPrefState(theme as ThemePref);
          writeStoredPref(theme as ThemePref); // refresh the boot cache
        }
      })
      .catch(() => {
        // degrade, never crash: the cached/local preference stands
      });
    return () => {
      active = false;
    };
  }, [ipc]);

  const setPref = useCallback(
    (next: ThemePref) => {
      setPrefState(next);
      writeStoredPref(next);
      ipc?.preferencesSet(next).catch(() => {});
    },
    [ipc],
  );

  const resolved: Theme = pref === "system" ? systemTheme : pref;
  return { pref, setPref, resolved };
}
