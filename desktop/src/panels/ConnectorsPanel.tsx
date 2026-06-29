import { useEffect, useState } from "react";
import { useIpc } from "../app/IpcProvider";
import type { ConnectorHealth, ConnectorList, ConnectorSync } from "../ipc/types";
import { connectorRows } from "./connectorView";

export function ConnectorsPanel() {
  const ipc = useIpc();
  const [list, setList] = useState<ConnectorList>({ connectors: [], problems: [] });
  const [health, setHealth] = useState<ConnectorHealth | null>(null);
  const [sync, setSync] = useState<ConnectorSync | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (ipc) {
      ipc
        .connectorsList()
        .then(setList)
        .catch(() => setList({ connectors: [], problems: [] }));
    }
  }, [ipc]);

  async function checkHealth() {
    if (!ipc) return;
    setBusy(true);
    try {
      setHealth(await ipc.connectorsHealth());
    } catch {
      setHealth(null);
    } finally {
      setBusy(false);
    }
  }

  async function runSync() {
    if (!ipc) return;
    setBusy(true);
    try {
      setSync(await ipc.connectorsSync());
    } catch {
      setSync(null);
    } finally {
      setBusy(false);
    }
  }

  const rows = connectorRows(list, health, sync);

  return (
    <div>
      <h1>Connectors</h1>
      <div className="row" style={{ gap: 8, marginBottom: 16 }}>
        <button onClick={checkHealth} disabled={!ipc || busy}>
          Check health
        </button>
        <button onClick={runSync} disabled={!ipc || busy}>
          Sync now
        </button>
      </div>
      {list.connectors.length === 0 && (
        <p className="muted">No connectors configured.</p>
      )}
      {rows.map((r) => (
        <div className="list-item" key={r.name}>
          <div>{r.name}</div>
          <div className="muted">
            {r.health === "unknown" ? "health unknown" : `health: ${r.detail || r.health}`}
            {r.written !== null && ` · ${r.written} written`}
          </div>
        </div>
      ))}
      {list.problems.map((p, i) => (
        <p className="muted" key={i}>
          ⚠ {p}
        </p>
      ))}
    </div>
  );
}
