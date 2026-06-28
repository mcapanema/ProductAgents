import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { IpcClient } from "../ipc/client";
import { createTauriClient } from "../ipc/transport";

const IpcContext = createContext<IpcClient | null>(null);

export function useIpc(): IpcClient | null {
  return useContext(IpcContext);
}

/** Provides a client. When `client` is given (tests), use it; else build the
 * Tauri-backed client once on mount. */
export function IpcProvider({
  client,
  children,
}: {
  client?: IpcClient;
  children: ReactNode;
}) {
  const [resolved, setResolved] = useState<IpcClient | null>(client ?? null);

  useEffect(() => {
    if (client) return;
    let active = true;
    createTauriClient().then((c) => {
      if (active) setResolved(c);
    });
    return () => {
      active = false;
    };
  }, [client]);

  return <IpcContext.Provider value={resolved}>{children}</IpcContext.Provider>;
}
