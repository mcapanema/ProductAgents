import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { IpcClient } from "./client";
import type { IpcMessage } from "./types";

/** True when running inside the Tauri shell (vs a plain browser / Vite dev server). */
export function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

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

/**
 * Dev fallback for a plain browser (the Vite dev server / Playwright): drive the
 * same IpcClient over a localhost WebSocket served by `productagents serve-ws`.
 * `WebSocketImpl` is injectable so the wiring is unit-testable without a real socket.
 */
export async function createWsClient(
  url = "ws://127.0.0.1:7420",
  WebSocketImpl: typeof WebSocket = WebSocket,
): Promise<IpcClient> {
  const ws = new WebSocketImpl(url);

  await new Promise<void>((resolve, reject) => {
    ws.onopen = () => resolve();
    ws.onerror = () =>
      reject(new Error(`IPC WebSocket failed to connect at ${url}`));
  });

  const subscribers: ((msg: IpcMessage) => void)[] = [];
  ws.onmessage = (event: MessageEvent) => {
    let msg: IpcMessage;
    try {
      msg = JSON.parse(String(event.data)) as IpcMessage;
    } catch {
      return; // a non-JSON line on the wire is ignored, not fatal
    }
    for (const sub of subscribers) sub(msg);
  };

  return new IpcClient(
    (line) => {
      ws.send(line);
      return Promise.resolve();
    },
    (cb) => {
      subscribers.push(cb);
    },
  );
}

/**
 * Build the right client for the environment: the Tauri sidecar inside the shell,
 * the dev WebSocket bridge when running in a plain browser (Vite dev / Playwright).
 */
export function createClient(): Promise<IpcClient> {
  return isTauri() ? createTauriClient() : createWsClient();
}

/**
 * Restart the backend after a workspace switch. In the Tauri shell this
 * respawns the sidecar (`ipc_restart`) so it re-resolves the active
 * workspace, then reloads the webview so every panel refetches. In the
 * browser/dev-bridge case only the page reloads — the `serve-ws` process
 * keeps its old workspace until restarted manually (dev-only limitation).
 */
export async function restartBackend(): Promise<void> {
  if (isTauri()) {
    await invoke<void>("ipc_restart");
  }
  window.location.reload();
}
