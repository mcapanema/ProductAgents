import { useState } from "react";
import { Button } from "antd";
import { isTauri } from "../ipc/transport";
import { updateStatusLabel, type UpdateState } from "./updateView";

// Lazy-imported inside the handler so the browser/Vitest bundles never pull the
// Tauri plugin (it has no web implementation). Degrades to a note off-desktop.
// The section heading comes from the enclosing Settings section — no label here.
export function UpdateSection() {
  const [state, setState] = useState<UpdateState>({ kind: "idle" });

  if (!isTauri()) {
    return <p className="muted">Auto-update is available in the desktop app.</p>;
  }

  async function checkAndInstall() {
    try {
      setState({ kind: "checking" });
      const { check } = await import("@tauri-apps/plugin-updater");
      const update = await check();
      if (!update) {
        setState({ kind: "none" });
        return;
      }
      setState({ kind: "available", version: update.version });
      setState({ kind: "installing" });
      await update.downloadAndInstall();
      const { relaunch } = await import("@tauri-apps/plugin-process");
      await relaunch();
    } catch (e) {
      setState({ kind: "error", message: e instanceof Error ? e.message : String(e) });
    }
  }

  const busy = state.kind === "checking" || state.kind === "installing";
  const label = updateStatusLabel(state);

  return (
    <div className="field">
      <Button onClick={checkAndInstall} loading={busy}>
        {busy ? "Working…" : "Check for updates"}
      </Button>
      {label && <p className={state.kind === "error" ? "error" : "muted"}>{label}</p>}
    </div>
  );
}
