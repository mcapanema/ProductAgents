import { useEffect, useState } from "react";
import { useIpc } from "../app/IpcProvider";
import type { ConfigStatus } from "../ipc/types";
import { UpdateSection } from "./UpdateSection";

export function SettingsPanel() {
  const ipc = useIpc();
  const [status, setStatus] = useState<ConfigStatus | null>(null);
  const [model, setModel] = useState("");
  const [provider, setProvider] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [saving, setSaving] = useState(false);

  function apply(s: ConfigStatus) {
    setStatus(s);
    setModel(s.model);
    setProvider(s.provider);
    setApiKey(""); // never echo a stored key
  }

  useEffect(() => {
    if (ipc) ipc.configGet().then(apply).catch(() => setStatus(null));
  }, [ipc]);

  function onProviderChange(id: string) {
    setProvider(id);
    const info = status?.providers.find((p) => p.id === id);
    if (info) setModel(info.default_model);
  }

  async function save() {
    if (!ipc) return;
    setSaving(true);
    // ponytail: derive provider from model prefix so the key lands under the right env var
    const effectiveProvider = model.includes(":") ? model.split(":")[0] : provider;
    try {
      apply(await ipc.configSet({ model, provider: effectiveProvider, api_key: apiKey }));
    } catch {
      // leave the form as-is; the status panel keeps the last known state
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <h1>Settings</h1>
      {status === null && <p className="muted">Loading configuration…</p>}
      {status && (
        <div style={{ maxWidth: 480 }}>
          <label className="field">
            <span>Model</span>
            <input aria-label="model" value={model} onChange={(e) => setModel(e.target.value)} />
          </label>
          <label className="field">
            <span>Provider</span>
            <select aria-label="provider" value={provider} onChange={(e) => onProviderChange(e.target.value)}>
              {status.providers.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>API key ({status.key_var})</span>
            <input
              aria-label="api key"
              type="password"
              placeholder={status.key_present ? "•••••• (set — leave blank to keep)" : "required"}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
          </label>
          <p className="muted">{status.key_present ? "Key present" : "No key set"}</p>
          {status.problems.map((p, i) => (
            <p className="error" key={i}>
              {p}
            </p>
          ))}
          <button className="primary" onClick={save} disabled={saving || !ipc}>
            {saving ? "Saving…" : "Save"}
          </button>
          <UpdateSection />
        </div>
      )}
    </div>
  );
}
