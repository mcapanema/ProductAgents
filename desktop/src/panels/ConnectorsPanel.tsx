import { useEffect, useState } from "react";
import { Button, Tag } from "antd";
import { useIpc } from "../app/IpcProvider";
import type { ConnectorConfigEntry, ConnectorHealth, ConnectorList, ConnectorSync } from "../ipc/types";
import {
  connectorStatus,
  isEnabled,
  lastSynced,
  mergeHealth,
  mergeSync,
  splitEntries,
  syncSummary,
  type ConnectorStatus,
} from "./connectorView";
import { ConnectorIcon } from "./connectorIcons";
import { ConnectorConfigForm } from "./ConnectorConfigForm";
import "./ConnectorsPanel.css";

/* Status badge — Phase 4A styleguide port (design/styleguide/src/phase4):
   pill with a 15% fill tint and a status dot, driven by the --ai-* tokens. */
function StatusBadge({ status }: { status: ConnectorStatus }) {
  return (
    <Tag bordered={false} className={`connector-badge connector-badge--${status.kind}`}>
      <span className="connector-badge__dot" aria-hidden="true" />
      {status.label}
    </Tag>
  );
}

function NavGroup({
  title,
  entries,
  health,
  selected,
  onSelect,
  withStatus,
}: {
  title: string;
  entries: ConnectorConfigEntry[];
  health: ConnectorHealth | null;
  selected: string | null;
  onSelect: (name: string) => void;
  withStatus: boolean;
}) {
  if (entries.length === 0) return null;
  return (
    <div className="settings-nav__group">
      <span className="settings-nav__title">{title}</span>
      <ul>
        {entries.map((e) => {
          const status = connectorStatus(e, health);
          return (
            <li key={e.connector}>
              <button
                type="button"
                className="settings-nav__item connectors-nav__item"
                aria-current={selected === e.connector ? "page" : undefined}
                onClick={() => onSelect(e.connector)}
              >
                <ConnectorIcon name={e.connector} size={16} />
                <span className="connectors-nav__label">{e.title ?? e.connector}</span>
                {withStatus && (
                  <span
                    className={`connector-dot connector-dot--${status.kind}`}
                    role="img"
                    aria-label={`${e.connector} ${status.label}`}
                  />
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function ConnectorsPanel() {
  const ipc = useIpc();
  const [entries, setEntries] = useState<ConnectorConfigEntry[]>([]);
  const [list, setList] = useState<ConnectorList | null>(null);
  const [health, setHealth] = useState<ConnectorHealth | null>(null);
  const [sync, setSync] = useState<ConnectorSync | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!ipc) return;
    ipc
      .connectorsConfigList()
      .then((es) => {
        setEntries(es);
        setSelected((s) => s ?? (splitEntries(es).enabled[0] ?? es[0])?.connector ?? null);
      })
      .catch(() => setEntries([]));
    ipc.connectorsList().then(setList).catch(() => setList(null));
  }, [ipc]);

  const { enabled, available } = splitEntries(entries);
  const entry = entries.find((e) => e.connector === selected) ?? null;

  async function checkHealth(name: string) {
    if (!ipc) return;
    setBusy(true);
    try {
      const report = await ipc.connectorsHealth(name);
      setHealth((prev) => mergeHealth(prev, report));
    } catch {
      // keep whatever we knew before — the badge stays as-is
    } finally {
      setBusy(false);
    }
  }

  async function runSync(name: string) {
    if (!ipc) return;
    setBusy(true);
    try {
      const report = await ipc.connectorsSync(name);
      setSync((prev) => mergeSync(prev, report));
      setList(await ipc.connectorsList()); // refresh last-synced stamps
    } catch {
      // keep the previous results
    } finally {
      setBusy(false);
    }
  }

  function onSaved(updated: ConnectorConfigEntry) {
    setEntries((es) => es.map((e) => (e.connector === updated.connector ? updated : e)));
  }

  const status = entry ? connectorStatus(entry, health) : null;
  const synced = entry ? syncSummary(entry.connector, sync) : null;
  const stamp = entry ? lastSynced(entry.connector, list) : null;

  return (
    <div className="connectors">
      <h1>Connectors</h1>
      <div className="settings-layout">
        <nav className="settings-nav" aria-label="Connectors">
          <NavGroup
            title="Enabled"
            entries={enabled}
            health={health}
            selected={selected}
            onSelect={setSelected}
            withStatus
          />
          <NavGroup
            title="Available"
            entries={available}
            health={health}
            selected={selected}
            onSelect={setSelected}
            withStatus={false}
          />
        </nav>
        <div className="settings-content">
          {entry && status ? (
            <>
              <header className="connector-detail__head">
                <ConnectorIcon name={entry.connector} size={28} />
                <h2 className="connector-detail__title">{entry.title ?? entry.connector}</h2>
                <StatusBadge status={status} />
                <span className="connector-detail__actions">
                  <Button onClick={() => checkHealth(entry.connector)} disabled={!ipc || busy} loading={busy}>
                    Check health
                  </Button>
                  <Button onClick={() => runSync(entry.connector)} disabled={!ipc || busy || !isEnabled(entry)} loading={busy}>
                    Sync now
                  </Button>
                </span>
              </header>
              {entry.description && <p className="muted">{entry.description}</p>}
              {status.detail && <p className="muted">{status.detail}</p>}
              {synced && <p className="muted">{synced}</p>}
              {stamp && <p className="muted">Last synced {stamp}</p>}
              <ConnectorConfigForm key={entry.connector} entry={entry} onSaved={onSaved} />
            </>
          ) : (
            <p className="muted">No connectors installed.</p>
          )}
          {list?.problems.map((p, i) => (
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
      </div>
    </div>
  );
}
