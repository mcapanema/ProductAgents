import { useState } from "react";
import { Button, Input, InputNumber, Switch } from "antd";
import { useIpc } from "../app/IpcProvider";
import type { ConnectorConfigEntry } from "../ipc/types";
import { blockFromFields, fieldsFromSchema } from "./connectorConfigView";

type SaveState = "idle" | "saving" | "saved" | "error";

/** Schema-driven config editor for one connector: enabled toggle, one control
 * per schema field, a companion secret-value input next to each `*_env` field,
 * and a Save button. Secrets are write-only — the server never echoes a value
 * back, so the password input always starts blank. Mount with
 * `key={entry.connector}` so edit state resets when the selection changes. */
export function ConnectorConfigForm({
  entry,
  onSaved,
}: {
  entry: ConnectorConfigEntry;
  onSaved: (updated: ConnectorConfigEntry) => void;
}) {
  const ipc = useIpc();
  const [edits, setEdits] = useState<Record<string, unknown>>({});
  const [secrets, setSecrets] = useState<Record<string, string>>({});
  const [enabled, setEnabled] = useState<boolean>(entry.config.enabled !== false);
  const [state, setState] = useState<SaveState>("idle");
  const [error, setError] = useState<string | null>(null);

  const fields = fieldsFromSchema(entry.schema);

  function patch(field: string, value: unknown) {
    setState("idle"); // stale "Saved" must not outlive an edit
    setEdits((e) => ({ ...e, [field]: value }));
  }

  function patchSecret(varName: string, value: string) {
    setState("idle");
    setSecrets((s) => ({ ...s, [varName]: value }));
  }

  async function save() {
    if (!ipc) return;
    setState("saving");
    const block = blockFromFields(entry, edits, enabled);
    const typed = Object.fromEntries(Object.entries(secrets).filter(([, v]) => v !== ""));
    try {
      const updated = await ipc.connectorsConfigSave(
        entry.connector,
        block,
        Object.keys(typed).length ? typed : undefined,
      );
      setEdits({});
      setSecrets({});
      setState("saved");
      onSaved(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setState("error");
    }
  }

  return (
    <section className="settings-section">
      <header className="settings-section__head settings-connector__head">
        <h2 className="settings-section__title">Configuration</h2>
        <span className="muted">{entry.installed ? "Installed" : "Not installed"}</span>
        <Switch
          aria-label={`${entry.connector} enabled`}
          checked={enabled}
          onChange={(v) => {
            setState("idle");
            setEnabled(v);
          }}
        />
      </header>
      <div className="settings-section__body">
        {fields.map((field) => {
          const value = edits[field.name] ?? entry.config[field.name] ?? "";
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
                      onChange={(v) => patch(field.name, v)}
                    />
                  ) : field.kind === "number" ? (
                    <InputNumber
                      aria-label={`${entry.connector} ${field.name}`}
                      value={typeof value === "number" ? value : undefined}
                      onChange={(v) => patch(field.name, v ?? undefined)}
                    />
                  ) : (
                    <Input
                      aria-label={`${entry.connector} ${field.name}`}
                      value={String(value)}
                      onChange={(e) => patch(field.name, e.target.value)}
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
                      value={secrets[value] ?? ""}
                      onChange={(e) => patchSecret(value, e.target.value)}
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
        {state === "error" && error && <p className="error">{error}</p>}
      </div>
      <div className="settings-footer">
        <Button
          type="primary"
          aria-label={`save ${entry.connector}`}
          onClick={save}
          loading={state === "saving"}
          disabled={state === "saving" || !ipc}
        >
          Save
        </Button>
        {state === "saved" && <span className="muted">Saved</span>}
      </div>
    </section>
  );
}
