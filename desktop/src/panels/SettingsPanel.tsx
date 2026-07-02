import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Button, Input, InputNumber, Select } from "antd";
import { useIpc } from "../app/IpcProvider";
import type { ConfigStatus, WorkspaceInfo } from "../ipc/types";
import { formFromStatus, originHint, paramsFromForm, type SettingsForm } from "./settingsView";
import { UpdateSection } from "./UpdateSection";
import { ThemeControl } from "../ui/ThemeControl";
import type { ThemePref } from "../ui/theme";
import "./SettingsPanel.css";

/* Section + preference-card structure ported from the design-system Phase 7
   styleguide (design/styleguide/src/phase7/): title/description over a
   hairline, each option as a label+caption row with its control on the right. */
function Section({ title, description, children }: { title: string; description?: string; children: ReactNode }) {
  return (
    <section className="settings-section">
      <header className="settings-section__head">
        <h2 className="settings-section__title">{title}</h2>
        {description && <p className="settings-section__desc">{description}</p>}
      </header>
      <div className="settings-section__body">{children}</div>
    </section>
  );
}

function Pref({ label, description, control }: { label: string; description?: string; control: ReactNode }) {
  return (
    <div className="settings-pref">
      <div className="settings-pref__meta">
        <span className="settings-pref__label">{label}</span>
        {description && <span className="settings-pref__desc">{description}</span>}
      </div>
      <div className="settings-pref__control">{control}</div>
    </div>
  );
}

type SectionId = "configuration" | "connectors" | "preferences" | "runtime" | "updates";

const NAV: { group: string; items: { id: SectionId; label: string }[] }[] = [
  {
    group: "Workspace",
    items: [
      { id: "configuration", label: "Configuration" },
      { id: "connectors", label: "Connectors" },
      { id: "preferences", label: "Preferences" },
    ],
  },
  {
    group: "Application",
    items: [
      { id: "runtime", label: "Runtime" },
      { id: "updates", label: "Updates" },
    ],
  },
];

function SettingsNav({ active, onSelect }: { active: SectionId; onSelect: (id: SectionId) => void }) {
  return (
    <nav className="settings-nav" aria-label="Settings sections">
      {NAV.map((group) => (
        <div key={group.group} className="settings-nav__group">
          <span className="settings-nav__title">{group.group}</span>
          <ul>
            {group.items.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className="settings-nav__item"
                  aria-current={active === item.id ? "page" : undefined}
                  onClick={() => onSelect(item.id)}
                >
                  {item.label}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}

export function SettingsPanel({
  theme,
  onThemeChange,
}: {
  theme: ThemePref;
  onThemeChange: (pref: ThemePref) => void;
}) {
  const ipc = useIpc();
  const [status, setStatus] = useState<ConfigStatus | null>(null);
  const [form, setForm] = useState<SettingsForm | null>(null);
  const [workspace, setWorkspace] = useState<WorkspaceInfo | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveState, setSaveState] = useState<"idle" | "saved" | "error">("idle");
  const [section, setSection] = useState<SectionId>("configuration");

  function apply(s: ConfigStatus) {
    setStatus(s);
    setForm(formFromStatus(s)); // secrets come back blank — never echoed
  }

  useEffect(() => {
    if (!ipc) return;
    ipc.configGet().then(apply).catch(() => setStatus(null));
    ipc.workspacesShow().then(setWorkspace).catch(() => setWorkspace(null));
  }, [ipc]);

  function patch(changes: Partial<SettingsForm>) {
    setSaveState("idle"); // stale "Saved" must not outlive an edit
    setForm((f) => (f ? { ...f, ...changes } : f));
  }

  function onProviderChange(id: string) {
    const info = status?.providers.find((p) => p.id === id);
    patch(info ? { provider: id, model: info.default_model } : { provider: id });
  }

  async function save() {
    if (!ipc || !form) return;
    setSaving(true);
    setSaveState("idle");
    try {
      apply(await ipc.configSet(paramsFromForm(form)));
      setSaveState("saved");
    } catch {
      // leave the form as-is; the status block keeps the last known state
      setSaveState("error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="settings">
      <h1>Settings</h1>
      <div className="settings-layout">
        <SettingsNav active={section} onSelect={setSection} />
        <div className="settings-content">
          {section === "configuration" && (status && form ? (
            <>
              <Section title="Model & Provider" description="Which LLM runs the pipeline. The model id's provider prefix wins over the dropdown.">
                <Pref
                  label="Provider"
                  control={
                    <Select
                      aria-label="provider"
                      value={form.provider}
                      onChange={onProviderChange}
                      style={{ width: 220 }}
                      options={status.providers.map((p) => ({ value: p.id, label: p.label }))}
                    />
                  }
                />
                <Pref
                  label="Model"
                  description={originHint(status.origins, "model") ?? "Provider-prefixed model id, e.g. anthropic:claude-sonnet-4-6."}
                  control={
                    <Input
                      aria-label="model"
                      value={form.model}
                      onChange={(e) => patch({ model: e.target.value })}
                      style={{ width: 320 }}
                    />
                  }
                />
                <Pref
                  label={`API key (${status.key_var})`}
                  description={status.key_present ? "Key present — leave blank to keep it." : "No key set."}
                  control={
                    <Input.Password
                      aria-label="api key"
                      placeholder={status.key_present ? "••••••" : "required"}
                      value={form.apiKey}
                      onChange={(e) => patch({ apiKey: e.target.value })}
                      style={{ width: 320 }}
                    />
                  }
                />
                {status.problems.map((p, i) => (
                  <p className="error" key={i}>
                    {p}
                  </p>
                ))}
              </Section>

              <Section title="Pipeline" description="Tuning knobs for the decision run. Stored in the workspace; changes apply to the next run.">
                <Pref
                  label="Debate rounds"
                  description={originHint(status.origins, "debate_rounds") ?? "One round = advocate argument + skeptic rebuttal. Default 2."}
                  control={
                    <InputNumber
                      aria-label="debate rounds"
                      min={1}
                      step={1}
                      value={form.debateRounds}
                      onChange={(v) => v !== null && patch({ debateRounds: v })}
                    />
                  }
                />
                <Pref
                  label="Judge threshold"
                  description={originHint(status.origins, "judge_threshold") ?? "Pass mark for evidence grounding and rationale coherence. Default 0.7."}
                  control={
                    <InputNumber
                      aria-label="judge threshold"
                      min={0}
                      max={1}
                      step={0.05}
                      value={form.judgeThreshold}
                      onChange={(v) => v !== null && patch({ judgeThreshold: v })}
                    />
                  }
                />
                <Pref
                  label="Judge max retries"
                  description={originHint(status.origins, "judge_max_retries") ?? "Strategist revisions a failing verdict may trigger. 0 = score-only. Default 1."}
                  control={
                    <InputNumber
                      aria-label="judge max retries"
                      min={0}
                      step={1}
                      value={form.judgeMaxRetries}
                      onChange={(v) => v !== null && patch({ judgeMaxRetries: v })}
                    />
                  }
                />
                <Pref
                  label="Provider max retries"
                  description={originHint(status.origins, "max_retries") ?? "Automatic retry-with-backoff budget for transient provider errors. Default 6."}
                  control={
                    <InputNumber
                      aria-label="provider max retries"
                      min={0}
                      step={1}
                      value={form.maxRetries}
                      onChange={(v) => v !== null && patch({ maxRetries: v })}
                    />
                  }
                />
              </Section>

              <div className="settings-footer">
                <Button type="primary" onClick={save} loading={saving} disabled={saving || !ipc}>
                  Save
                </Button>
                {saveState === "saved" && <span className="muted">Saved</span>}
                {saveState === "error" && <span className="error">Save failed — settings unchanged.</span>}
              </div>
            </>
          ) : (
            <p className="muted">Loading configuration…</p>
          ))}
          {section === "connectors" && <div data-section="connectors" />}
          {section === "preferences" && (
            <Section title="Preferences" description="Personal to this workspace; never affects workflow execution.">
              <Pref label="Theme" control={<ThemeControl value={theme} onChange={onThemeChange} />} />
            </Section>
          )}
          {section === "runtime" && (
            <Section title="Runtime" description="Application bootstrap configuration — read-only here; edit the workspace .env or export the variables.">
              {workspace ? (
                <>
                  <Pref label="Name" control={<code className="settings-path">{workspace.name}</code>} />
                  <Pref label="Database" control={<code className="settings-path">{workspace.db_url}</code>} />
                  <Pref label="Connectors file" control={<code className="settings-path">{workspace.connectors_file}</code>} />
                  <Pref label="Env file" control={<code className="settings-path">{workspace.env_file}</code>} />
                  <Pref label="Log file" control={<code className="settings-path">{workspace.log_file}</code>} />
                  <Pref label="Prompt overrides" control={<code className="settings-path">{workspace.prompts_dir}</code>} />
                </>
              ) : (
                <p className="muted">Workspace details unavailable.</p>
              )}
            </Section>
          )}
          {section === "updates" && (
            <Section title="Updates"><UpdateSection /></Section>
          )}
        </div>
      </div>
    </div>
  );
}
