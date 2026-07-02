import { useEffect, useState } from "react";
import { Button, Input, InputNumber, Switch } from "antd";
import { useIpc } from "../app/IpcProvider";
import type { ConnectorConfigEntry } from "../ipc/types";
import { blockFromFields, fieldsFromSchema } from "./connectorConfigView";

type SaveState = "idle" | "saving" | "saved" | "error";

/** Schema-driven per-connector config editor. One card per installed connector:
 * enabled toggle, one control per schema field, a companion secret-value input
 * next to each `*_env` field, and a Save button. Secrets are write-only — the
 * server never echoes a value back, so the password input always starts blank. */
export function SettingsConnectors() {
  const ipc = useIpc();
  const [entries, setEntries] = useState<ConnectorConfigEntry[]>([]);
  const [edits, setEdits] = useState<Record<string, Record<string, unknown>>>({});
  const [enabled, setEnabled] = useState<Record<string, boolean>>({});
  const [secrets, setSecrets] = useState<Record<string, Record<string, string>>>({});
  const [saveState, setSaveState] = useState<Record<string, SaveState>>({});
  const [saveError, setSaveError] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!ipc) return;
    ipc.connectorsConfigList().then(setEntries).catch(() => setEntries([]));
  }, [ipc]);

  function isEnabled(entry: ConnectorConfigEntry): boolean {
    return enabled[entry.connector] ?? entry.config.enabled !== false;
  }

  function patch(connector: string, field: string, value: unknown) {
    setSaveState((s) => ({ ...s, [connector]: "idle" }));
    setEdits((e) => ({ ...e, [connector]: { ...e[connector], [field]: value } }));
  }

  function patchSecret(connector: string, varName: string, value: string) {
    setSaveState((s) => ({ ...s, [connector]: "idle" }));
    setSecrets((s) => ({ ...s, [connector]: { ...s[connector], [varName]: value } }));
  }

  function toggleEnabled(connector: string, value: boolean) {
    setSaveState((s) => ({ ...s, [connector]: "idle" }));
    setEnabled((e) => ({ ...e, [connector]: value }));
  }

  async function save(entry: ConnectorConfigEntry) {
    if (!ipc) return;
    const connector = entry.connector;
    setSaveState((s) => ({ ...s, [connector]: "saving" }));
    const block = blockFromFields(entry, edits[connector] ?? {}, isEnabled(entry));
    const typed = Object.fromEntries(
      Object.entries(secrets[connector] ?? {}).filter(([, v]) => v !== ""),
    );
    try {
      const updated = await ipc.connectorsConfigSave(
        connector,
        block,
        Object.keys(typed).length ? typed : undefined,
      );
      setEntries((es) => es.map((e) => (e.connector === connector ? updated : e)));
      setEdits((e) => ({ ...e, [connector]: {} }));
      setSecrets((s) => ({ ...s, [connector]: {} }));
      setEnabled((e) => {
        const next = { ...e };
        delete next[connector];
        return next;
      });
      setSaveState((s) => ({ ...s, [connector]: "saved" }));
    } catch (err) {
      setSaveError((e) => ({ ...e, [connector]: err instanceof Error ? err.message : String(err) }));
      setSaveState((s) => ({ ...s, [connector]: "error" }));
    }
  }

  if (entries.length === 0) {
    return <p className="muted">No connectors installed.</p>;
  }

  return (
    <div className="settings-connectors">
      {entries.map((entry) => {
        const fields = fieldsFromSchema(entry.schema);
        const connectorEdits = edits[entry.connector] ?? {};
        const connectorSecrets = secrets[entry.connector] ?? {};
        const state = saveState[entry.connector] ?? "idle";
        return (
          <section className="settings-section" key={entry.connector}>
            <header className="settings-section__head settings-connector__head">
              <h2 className="settings-section__title">{entry.connector}</h2>
              <span className="muted">{entry.installed ? "Installed" : "Not installed"}</span>
              <Switch
                aria-label={`${entry.connector} enabled`}
                checked={isEnabled(entry)}
                onChange={(value) => toggleEnabled(entry.connector, value)}
              />
            </header>
            <div className="settings-section__body">
              {fields.map((field) => {
                const value = connectorEdits[field.name] ?? entry.config[field.name] ?? "";
                return (
                  <div key={field.name}>
                    <div className="settings-pref">
                      <div className="settings-pref__meta">
                        <span className="settings-pref__label">
                          {field.name}
                          {field.required ? " *" : ""}
                        </span>
                      </div>
                      <div className="settings-pref__control">
                        {field.kind === "boolean" ? (
                          <Switch
                            aria-label={`${entry.connector} ${field.name}`}
                            checked={Boolean(value)}
                            onChange={(v) => patch(entry.connector, field.name, v)}
                          />
                        ) : field.kind === "number" ? (
                          <InputNumber
                            aria-label={`${entry.connector} ${field.name}`}
                            value={typeof value === "number" ? value : undefined}
                            onChange={(v) => patch(entry.connector, field.name, v ?? undefined)}
                          />
                        ) : (
                          <Input
                            aria-label={`${entry.connector} ${field.name}`}
                            value={String(value)}
                            onChange={(e) => patch(entry.connector, field.name, e.target.value)}
                          />
                        )}
                      </div>
                    </div>
                    {field.secretRef && typeof value === "string" && value && (
                      <div className="settings-pref">
                        <div className="settings-pref__meta">
                          <span className="settings-pref__label">Secret value</span>
                          <span className="settings-pref__desc">Stored in the workspace .env, never displayed.</span>
                        </div>
                        <div className="settings-pref__control">
                          <Input.Password
                            aria-label={`${entry.connector} secret ${value}`}
                            placeholder="value stays in .env"
                            value={connectorSecrets[value] ?? ""}
                            onChange={(e) => patchSecret(entry.connector, value, e.target.value)}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
              {entry.problems.map((p, i) => (
                <p className="error" key={i}>
                  {p}
                </p>
              ))}
              {state === "error" && saveError[entry.connector] && (
                <p className="error">{saveError[entry.connector]}</p>
              )}
            </div>
            <div className="settings-footer">
              <Button
                type="primary"
                aria-label={`save ${entry.connector}`}
                onClick={() => save(entry)}
                loading={state === "saving"}
                disabled={state === "saving" || !ipc}
              >
                Save
              </Button>
              {state === "saved" && <span className="muted">Saved</span>}
            </div>
          </section>
        );
      })}
    </div>
  );
}
