import { useEffect, useState } from "react";
import { Button, Table } from "antd";
import type { TableColumnsType } from "antd";
import { useIpc } from "../app/IpcProvider";
import type { ConnectorHealth, ConnectorList, ConnectorSync } from "../ipc/types";
import { connectorRows } from "./connectorView";

type ConnectorRow = ReturnType<typeof connectorRows>[number];

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

  const columns: TableColumnsType<ConnectorRow> = [
    { title: "Connector", dataIndex: "name", key: "name" },
    {
      title: "Status",
      key: "status",
      render: (_, r) => (
        <span className="muted">
          {r.health === "unknown" ? "health unknown" : `health: ${r.detail || r.health}`}
          {r.synced === "error"
            ? ` · ⚠ ${r.error}`
            : r.written !== null && ` · ${r.written} written`}
          {r.lastSynced && ` · last sync ${r.lastSynced}`}
        </span>
      ),
    },
  ];

  return (
    <div>
      <h1>Connectors</h1>
      <div className="row" style={{ gap: 8, marginBottom: 16 }}>
        <Button onClick={checkHealth} disabled={!ipc || busy} loading={busy}>
          Check health
        </Button>
        <Button onClick={runSync} disabled={!ipc || busy} loading={busy}>
          Sync now
        </Button>
      </div>
      {list.connectors.length === 0 && <p className="muted">No connectors configured.</p>}
      {rows.length > 0 && (
        <Table<ConnectorRow> columns={columns} dataSource={rows} rowKey="name" pagination={false} size="middle" />
      )}
      {list.problems.map((p, i) => (
        <p className="muted" key={`list-${i}`}>
          ⚠ {p}
        </p>
      ))}
      {health?.problems.map((p, i) => (
        <p className="muted" key={`health-${i}`}>
          ⚠ {p}
        </p>
      ))}
      {sync?.problems.map((p, i) => (
        <p className="muted" key={`sync-${i}`}>
          ⚠ {p}
        </p>
      ))}
    </div>
  );
}
