import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { IpcClient } from "./client";
import type { IpcMessage } from "./types";

/**
 * Build an IpcClient bound to the live Tauri sidecar: each `ipc://message`
 * event payload is one decoded response line; `ipc_send` writes request lines.
 */
export async function createTauriClient(): Promise<IpcClient> {
  const subscribers: ((msg: IpcMessage) => void)[] = [];

  await listen<string>("ipc://message", (event) => {
    let msg: IpcMessage;
    try {
      msg = JSON.parse(event.payload) as IpcMessage;
    } catch {
      return; // a non-JSON line on the wire is ignored, not fatal
    }
    for (const sub of subscribers) sub(msg);
  });

  return new IpcClient(
    (line) => invoke<void>("ipc_send", { line }),
    (cb) => {
      subscribers.push(cb);
    },
  );
}
