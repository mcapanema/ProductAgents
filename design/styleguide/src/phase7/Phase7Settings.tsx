// Phase 7 — Settings components. The desktop app's one settings surface today
// (`desktop/src/panels/SettingsPanel.tsx`) reads/writes model + provider + API
// key via `config.get`/`config.set` IPC; Provider/Model Configuration and API
// Key Input are grounded in that real shape (`ConfigStatus`/`ProviderInfo`,
// `desktop/src/ipc/types.ts`). Theme Selector, Keyboard-Shortcut Editor, MCP
// Server Configuration, and the Environment-Variable Editor have no backend
// yet — forward-looking, same posture as Phase 6's git/file-tree state.
//
// Security posture (API Key Input + secret rows in the Environment-Variable
// Editor): a stored secret is NEVER echoed back by the platform, so these
// components never hold one in state either — the input starts empty, a
// placeholder communicates "a value is set", and the reveal toggle can only
// show what the user just typed (disabled while the field is empty). Built
// from the Phase-2 token layer only (no new colours).
import { useState } from "react";
import type { CSSProperties, KeyboardEvent as ReactKeyboardEvent } from "react";
import type { Density } from "../sg";
import { Section, Specimen } from "../sg";
import "./phase7-settings.css";

const vars = (o: Record<string, string>): CSSProperties => o as CSSProperties;

/* ── Icons ──────────────────────────────────────────────────────────────────── */

type IconName =
  | "gear"
  | "monitor"
  | "sun"
  | "moon"
  | "key"
  | "command"
  | "plug"
  | "terminal"
  | "plus"
  | "trash"
  | "pencil"
  | "eye"
  | "eye-off"
  | "check-circle"
  | "alert-triangle"
  | "x-circle"
  | "chevron-down";

const PATHS: Record<IconName, React.ReactNode> = {
  gear: <><circle cx="12" cy="12" r="3" /><path d="M19.4 13a1.7 1.7 0 00.3 1.9l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.9-.3 1.7 1.7 0 00-1 1.5V19a2 2 0 11-4 0v-.2a1.7 1.7 0 00-1-1.5 1.7 1.7 0 00-1.9.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.9 1.7 1.7 0 00-1.5-1H3a2 2 0 110-4h.2a1.7 1.7 0 001.5-1 1.7 1.7 0 00-.3-1.9l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.9.3H9a1.7 1.7 0 001-1.5V3a2 2 0 114 0v.2a1.7 1.7 0 001 1.5 1.7 1.7 0 001.9-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.9V9a1.7 1.7 0 001.5 1H21a2 2 0 110 4h-.2a1.7 1.7 0 00-1.4 1z" /></>,
  monitor: <><rect x="3" y="4" width="18" height="13" rx="1.5" /><path d="M8 21h8M12 17v4" /></>,
  sun: <><circle cx="12" cy="12" r="4.5" /><path d="M12 2v2.5M12 19.5V22M4.2 4.2l1.8 1.8M18 18l1.8 1.8M2 12h2.5M19.5 12H22M4.2 19.8l1.8-1.8M18 6l1.8-1.8" /></>,
  moon: <path d="M20 14.5A8.5 8.5 0 1110 4a6.8 6.8 0 0010 10.5z" />,
  key: <><circle cx="8" cy="15" r="4" /><path d="M11 12l8.5-8.5M16 7l2.5 2.5M19 4l1.5 1.5" /></>,
  command: <><rect x="4" y="4" width="16" height="16" rx="3" /><path d="M9 8v8M15 8v8M9 12h6" /></>,
  plug: <><path d="M9 3v6M15 3v6M6 9h12v3a6 6 0 01-12 0V9z" /><path d="M12 18v3" /></>,
  terminal: <><rect x="3" y="4" width="18" height="16" rx="1.5" /><path d="M7 9l3.5 3L7 15M12.5 15h5" /></>,
  plus: <path d="M12 5v14M5 12h14" />,
  trash: <><path d="M4 7h16M9 7V5a1 1 0 011-1h4a1 1 0 011 1v2m1 0v12a1 1 0 01-1 1H8a1 1 0 01-1-1V7h10z" /><path d="M10 11v6M14 11v6" /></>,
  pencil: <><path d="M4 20l.9-3.6L16 5.3l2.7 2.7L7.6 19.1 4 20z" /><path d="M14 7.3l2.7 2.7" /></>,
  eye: <><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z" /><circle cx="12" cy="12" r="3" /></>,
  "eye-off": <><path d="M10.6 6.2A9.7 9.7 0 0112 6c6.4 0 10 6 10 6a17 17 0 01-2.4 3" /><path d="M6.3 6.4A17 17 0 002 12s3.6 7 10 7a9.7 9.7 0 003.2-.5" /><line x1="3" y1="3" x2="21" y2="21" /></>,
  "check-circle": <><circle cx="12" cy="12" r="8" /><path d="M8.5 12.5l2.3 2.3L16 9.5" /></>,
  "alert-triangle": <><path d="M12 4l9 16H3z" /><path d="M12 10v4" /><path d="M12 17h.01" /></>,
  "x-circle": <><circle cx="12" cy="12" r="8" /><path d="M9 9l6 6M15 9l-6 6" /></>,
  "chevron-down": <path d="M6 9l6 6 6-6" />,
};

function Icon({ name, size = "sm" }: { name: IconName; size?: "xs" | "sm" | "md" }) {
  return (
    <svg
      className={`p7-ico p7-ico--${size}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {PATHS[name]}
    </svg>
  );
}

// `<select>` left at appearance:auto fights its own box model (the native
// widget ignores our padding/height for text layout), cropping and
// flickering the label. appearance:none hands layout fully to CSS — same
// fix Phase 3C's fm-select uses — with a decorative caret standing in for
// the native arrow.
// `block`: fill the field's width (paired with a sibling full-width input,
// e.g. Provider/Model Configuration). Omit it to size to content, e.g. inside
// a Preference Card row that shouldn't stretch.
function Select({ value, onChange, options, label, block = false }: {
  value: string; onChange: (v: string) => void; options: { value: string; label: string }[]; label: string; block?: boolean;
}) {
  return (
    <span className={block ? "p7-select-wrap p7-select-wrap--block" : "p7-select-wrap"}>
      <select className="p7-select" value={value} onChange={(e) => onChange(e.target.value)} aria-label={label}>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
      <span className="p7-select-caret"><Icon name="chevron-down" size="xs" /></span>
    </span>
  );
}

/* ── 1. Settings Navigation ────────────────────────────────────────────────── */

interface NavItem { id: string; label: string; icon: IconName }

const NAV_ITEMS: NavItem[] = [
  { id: "general", label: "General", icon: "gear" },
  { id: "appearance", label: "Appearance", icon: "monitor" },
  { id: "providers", label: "Providers & Models", icon: "key" },
  { id: "keyboard", label: "Keyboard", icon: "command" },
  { id: "mcp", label: "MCP Servers", icon: "plug" },
  { id: "environment", label: "Environment", icon: "terminal" },
];

function SettingsNavigation({ active, onSelect }: { active: string; onSelect: (id: string) => void }) {
  return (
    <nav className="p7-nav" aria-label="Settings sections">
      <ul>
        {NAV_ITEMS.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              className="p7-nav__item"
              aria-current={active === item.id ? "page" : undefined}
              onClick={() => onSelect(item.id)}
            >
              <Icon name={item.icon} size="sm" />
              {item.label}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}

/* ── 2. Section ─────────────────────────────────────────────────────────────── */

function SettingsSection({ title, description, children }: { title: string; description?: string; children: React.ReactNode }) {
  return (
    <div className="p7-section">
      <header className="p7-section__head">
        <h4 className="p7-section__title">{title}</h4>
        {description && <p className="p7-section__desc">{description}</p>}
      </header>
      <div className="p7-section__body">{children}</div>
    </div>
  );
}

/* ── 3. Preference Card (+ Switch) ─────────────────────────────────────────── */

function Switch({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      className="p7-switch"
      data-on={checked}
      onClick={() => onChange(!checked)}
    >
      <span className="p7-switch__knob" />
    </button>
  );
}

function PreferenceCard({ label, description, control }: { label: string; description?: string; control: React.ReactNode }) {
  return (
    <div className="p7-pref">
      <div className="p7-pref__meta">
        <span className="p7-pref__label">{label}</span>
        {description && <span className="p7-pref__desc">{description}</span>}
      </div>
      <div className="p7-pref__control">{control}</div>
    </div>
  );
}

function PreferenceCardDemo() {
  const [autosave, setAutosave] = useState(true);
  const [telemetry, setTelemetry] = useState(false);
  const [density, setDensity] = useState("comfortable");
  return (
    <div className="p7-pref-list">
      <PreferenceCard
        label="Auto-save sessions"
        description="Persist the reasoning timeline to the Event Store as a run streams."
        control={<Switch checked={autosave} onChange={setAutosave} label="Auto-save sessions" />}
      />
      <PreferenceCard
        label="Share anonymous usage telemetry"
        description="No initiative text or evidence ever leaves the machine."
        control={<Switch checked={telemetry} onChange={setTelemetry} label="Share anonymous usage telemetry" />}
      />
      <PreferenceCard
        label="Default density"
        description="Applies to every resource panel; overridable per view."
        control={
          <Select
            value={density}
            onChange={setDensity}
            label="Default density"
            options={[{ value: "comfortable", label: "Comfortable" }, { value: "compact", label: "Compact" }]}
          />
        }
      />
    </div>
  );
}

/* ── 4. Theme Selector ─────────────────────────────────────────────────────── */

type ThemeChoice = "light" | "dark" | "system";

const THEME_OPTIONS: { value: ThemeChoice; label: string; icon: IconName }[] = [
  { value: "light", label: "Light", icon: "sun" },
  { value: "dark", label: "Dark", icon: "moon" },
  { value: "system", label: "System", icon: "monitor" },
];

function ThemeSelector({ value, onChange }: { value: ThemeChoice; onChange: (v: ThemeChoice) => void }) {
  return (
    <div className="p7-theme" role="radiogroup" aria-label="Theme">
      {THEME_OPTIONS.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          className="p7-theme__opt"
          data-active={value === o.value}
          onClick={() => onChange(o.value)}
        >
          <Icon name={o.icon} size="sm" />
          {o.label}
        </button>
      ))}
    </div>
  );
}

function ThemeSelectorDemo() {
  const [theme, setTheme] = useState<ThemeChoice>("light");
  return <ThemeSelector value={theme} onChange={setTheme} />;
}

/* ── 5. Keyboard-Shortcut Editor ───────────────────────────────────────────── */

interface ShortcutData { id: string; action: string; keys: string[] }

const SHORTCUTS: ShortcutData[] = [
  { id: "palette", action: "Open command palette", keys: ["⌘", "K"] },
  { id: "approve", action: "Approve pending decision", keys: ["⌘", "Enter"] },
  { id: "new-run", action: "Start a new run", keys: ["⌘", "N"] },
  { id: "search", action: "Search sessions", keys: ["⌘", "F"] },
];

function ShortcutRow({ data, recording, onStartRecord, onCancelRecord }: {
  data: ShortcutData; recording: boolean; onStartRecord: () => void; onCancelRecord: () => void;
}) {
  return (
    <li className="p7-shortcut-row">
      <span className="p7-shortcut-row__action">{data.action}</span>
      {recording ? (
        <span className="p7-shortcut-row__capture" role="status">Press a key… (Esc to cancel)</span>
      ) : (
        <span className="p7-shortcut-row__keys">
          {data.keys.map((k, i) => <kbd key={i} className="p7-kbd">{k}</kbd>)}
        </span>
      )}
      <button
        type="button"
        className="p7-icon-btn"
        aria-label={recording ? `Cancel editing ${data.action}` : `Edit shortcut for ${data.action}`}
        onClick={recording ? onCancelRecord : onStartRecord}
      >
        <Icon name="pencil" size="xs" />
      </button>
    </li>
  );
}

const BARE_MODIFIERS = new Set(["Control", "Shift", "Alt", "Meta"]);

function formatKeyLabel(key: string): string {
  if (key === " ") return "Space";
  return key.length === 1 ? key.toUpperCase() : key;
}

// A bare modifier press (e.g. just tapping Cmd) isn't a complete binding —
// keep waiting until a non-modifier key arrives, then combine it with
// whichever modifiers are still held.
function describeKeyCombo(e: ReactKeyboardEvent): string[] | null {
  if (BARE_MODIFIERS.has(e.key)) return null;
  const keys: string[] = [];
  if (e.metaKey) keys.push("⌘");
  if (e.ctrlKey) keys.push("Ctrl");
  if (e.altKey) keys.push("⌥");
  if (e.shiftKey) keys.push("⇧");
  keys.push(formatKeyLabel(e.key));
  return keys;
}

function KeyboardShortcutEditor() {
  const [shortcuts, setShortcuts] = useState(SHORTCUTS);
  const [recordingId, setRecordingId] = useState<string | null>(null);

  function onKeyDownCapture(e: ReactKeyboardEvent<HTMLUListElement>) {
    if (!recordingId) return;
    if (e.key === "Escape") {
      e.preventDefault();
      setRecordingId(null);
      return;
    }
    const combo = describeKeyCombo(e);
    if (!combo) return; // bare modifier — still waiting for the real key
    e.preventDefault();
    setShortcuts((prev) => prev.map((s) => (s.id === recordingId ? { ...s, keys: combo } : s)));
    setRecordingId(null);
  }

  return (
    <ul className="p7-shortcut-list" onKeyDown={onKeyDownCapture}>
      {shortcuts.map((s) => (
        <ShortcutRow
          key={s.id}
          data={s}
          recording={recordingId === s.id}
          onStartRecord={() => setRecordingId(s.id)}
          onCancelRecord={() => setRecordingId(null)}
        />
      ))}
    </ul>
  );
}

/* ── 6. Provider/Model Configuration ───────────────────────────────────────── */

interface ProviderOption { id: string; label: string; key_var: string; default_model: string }

// Mirrors ProviderInfo (desktop/src/ipc/types.ts) and config.get's providers list.
const PROVIDERS: ProviderOption[] = [
  { id: "anthropic", label: "Anthropic", key_var: "ANTHROPIC_API_KEY", default_model: "anthropic:claude-sonnet-4-6" },
  { id: "openai", label: "OpenAI", key_var: "OPENAI_API_KEY", default_model: "openai:gpt-5" },
  { id: "google_genai", label: "Google", key_var: "GOOGLE_API_KEY", default_model: "google_genai:gemini-2.5-pro" },
];

function ProviderModelConfig() {
  const [providerId, setProviderId] = useState(PROVIDERS[0].id);
  const provider = PROVIDERS.find((p) => p.id === providerId)!;
  const [model, setModel] = useState(provider.default_model);

  function onProviderChange(id: string) {
    setProviderId(id);
    const next = PROVIDERS.find((p) => p.id === id);
    if (next) setModel(next.default_model);
  }

  return (
    <div className="p7-provider">
      <label className="p7-field">
        <span className="p7-field__label">Provider</span>
        <Select
          value={providerId}
          onChange={onProviderChange}
          label="Provider"
          options={PROVIDERS.map((p) => ({ value: p.id, label: p.label }))}
          block
        />
      </label>
      <label className="p7-field">
        <span className="p7-field__label">Model</span>
        <input className="p7-input p7-input--mono" value={model} onChange={(e) => setModel(e.target.value)} aria-label="model" />
      </label>
      <p className="p7-hint">
        Sets <code className="p7-code">PRODUCTAGENTS_MODEL</code>; provider is derived from the model's
        <code className="p7-code">{providerId}:…</code> prefix when present, else the selection above.
      </p>
    </div>
  );
}

/* ── 7. MCP Server Configuration ───────────────────────────────────────────── */

type McpStatus = "connected" | "error" | "disconnected";

interface McpServerData { id: string; name: string; command: string; status: McpStatus }

const MCP_SERVERS: McpServerData[] = [
  { id: "github", name: "github", command: "npx -y @modelcontextprotocol/server-github", status: "connected" },
  { id: "jira", name: "jira", command: "uvx mcp-server-jira", status: "error" },
  { id: "fs", name: "filesystem", command: "npx -y @modelcontextprotocol/server-filesystem ~/workspaces", status: "disconnected" },
];

const MCP_STATUS_CFG: Record<McpStatus, { label: string; icon: IconName }> = {
  connected: { label: "Connected", icon: "check-circle" },
  error: { label: "Error", icon: "x-circle" },
  disconnected: { label: "Disconnected", icon: "alert-triangle" },
};

function McpServerRow({ data }: { data: McpServerData }) {
  const cfg = MCP_STATUS_CFG[data.status];
  return (
    <li className="p7-mcp-row">
      <Icon name="plug" size="sm" />
      <span className="p7-mcp-row__meta">
        <span className="p7-mcp-row__name">{data.name}</span>
        <span className="p7-mcp-row__cmd">{data.command}</span>
      </span>
      <span className="p7-mcp-row__status" data-status={data.status}>
        <Icon name={cfg.icon} size="xs" />
        {cfg.label}
      </span>
      <button type="button" className="p7-icon-btn" aria-label={`Remove ${data.name}`}>
        <Icon name="trash" size="xs" />
      </button>
    </li>
  );
}

function McpServerConfig() {
  return (
    <div className="p7-mcp">
      <ul className="p7-mcp-list">
        {MCP_SERVERS.map((s) => <McpServerRow key={s.id} data={s} />)}
      </ul>
      <button type="button" className="p7-add-row">
        <Icon name="plus" size="xs" /> Add MCP server
      </button>
    </div>
  );
}

/* ── 8. Environment-Variable Editor ────────────────────────────────────────── */

interface EnvVarData { id: string; key: string; value: string; secret: boolean }

const ENV_VARS: EnvVarData[] = [
  { id: "1", key: "PRODUCTAGENTS_WORKSPACE", value: "default", secret: false },
  { id: "2", key: "PRODUCTAGENTS_LOG_LEVEL", value: "INFO", secret: false },
  { id: "3", key: "ANTHROPIC_API_KEY", value: "", secret: true },
];

function EnvVarRow({ data }: { data: EnvVarData }) {
  const [value, setValue] = useState(data.value); // secret rows start empty — never echo a stored value
  const [revealed, setRevealed] = useState(false);
  return (
    <li className="p7-envvar-row">
      <input className="p7-input p7-input--mono" defaultValue={data.key} aria-label="variable name" />
      <input
        className="p7-input p7-input--mono"
        type={data.secret && !revealed ? "password" : "text"}
        placeholder={data.secret ? "•••••••• (set — leave blank to keep)" : undefined}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        aria-label={`value for ${data.key}`}
        autoComplete="off"
      />
      {data.secret && (
        <button
          type="button"
          className="p7-icon-btn"
          aria-label={revealed ? "Hide value" : "Reveal value"}
          onClick={() => setRevealed((v) => !v)}
          disabled={value === ""}
        >
          <Icon name={revealed ? "eye-off" : "eye"} size="xs" />
        </button>
      )}
      <button type="button" className="p7-icon-btn" aria-label={`Remove ${data.key}`}>
        <Icon name="trash" size="xs" />
      </button>
    </li>
  );
}

function EnvironmentVariableEditor() {
  return (
    <div className="p7-envvar">
      <ul className="p7-envvar-list">
        {ENV_VARS.map((v) => <EnvVarRow key={v.id} data={v} />)}
      </ul>
      <button type="button" className="p7-add-row">
        <Icon name="plus" size="xs" /> Add variable
      </button>
    </div>
  );
}

/* ── 9. API Key Input ──────────────────────────────────────────────────────── */

function ApiKeyInput({ keyVar, present }: { keyVar: string; present: boolean }) {
  const [value, setValue] = useState(""); // never pre-filled from a stored secret
  const [revealed, setRevealed] = useState(false);
  return (
    <div className="p7-apikey">
      <label className="p7-field">
        <span className="p7-field__label">
          API key <span className="p7-field__hint">({keyVar})</span>
        </span>
        <span className="p7-apikey__row">
          <input
            className="p7-input p7-input--mono"
            type={revealed ? "text" : "password"}
            placeholder={present ? "•••••••• (set — leave blank to keep)" : "required"}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            aria-label="api key"
            autoComplete="off"
          />
          <button
            type="button"
            className="p7-icon-btn"
            aria-label={revealed ? "Hide key" : "Reveal key"}
            onClick={() => setRevealed((v) => !v)}
            disabled={value === ""}
          >
            <Icon name={revealed ? "eye-off" : "eye"} size="xs" />
          </button>
        </span>
      </label>
      <span className="p7-apikey__status" data-present={present}>
        <Icon name={present ? "check-circle" : "alert-triangle"} size="xs" />
        {present ? "Key present" : "No key set"}
      </span>
    </div>
  );
}

/* ── Composed: a settings page (nav + section body), for the Navigation specimen ── */

function SettingsPageDemo() {
  const [active, setActive] = useState("general");
  return (
    <div className="p7-shell" style={vars({ "--p7-shell-h": "320px" })}>
      <SettingsNavigation active={active} onSelect={setActive} />
      <div className="p7-shell__body">
        <SettingsSection title={NAV_ITEMS.find((n) => n.id === active)?.label ?? ""} description="Composed from Settings Navigation + Section, swapping body content per item.">
          <p className="p7-hint">Selecting an item on the left swaps this panel's content — the rest of this gallery shows each piece in isolation.</p>
        </SettingsSection>
      </div>
    </div>
  );
}

/* ── Gallery ────────────────────────────────────────────────────────────────── */

export function Phase7Settings({ density }: { density: Density }) {
  return (
    <div data-density={density}>
      <div className="sg-intro">
        <h2>Settings components</h2>
        <p>
          Configuration surfaces: navigating settings, grouping related
          preferences, switching theme, rebinding shortcuts, choosing a model
          provider, wiring MCP servers, editing environment variables, and the
          one security-sensitive input — an API key. Reuses the existing
          status/semantic tokens — no new colours.
        </p>
      </div>

      <Section id="p7-nav" title="Settings Navigation" desc="The settings sidebar: one entry per resource, active item marked. Composed here with Section into a full settings-page layout.">
        <Specimen label="default"><SettingsPageDemo /></Specimen>
      </Section>

      <Section id="p7-section" title="Section" desc="A titled, divided group within a settings page — heading, optional description, body.">
        <Specimen label="default">
          <SettingsSection title="Notifications" description="Control when ProductAgents interrupts you.">
            <p className="p7-hint">Section bodies typically hold one or more Preference Cards.</p>
          </SettingsSection>
        </Specimen>
      </Section>

      <Section id="p7-pref" title="Preference Card" desc="A labelled setting row pairing a description with its control — a switch, a select, or a composed control like Theme Selector.">
        <Specimen label="default"><PreferenceCardDemo /></Specimen>
      </Section>

      <Section id="p7-theme" title="Theme Selector" desc="Three-way choice — Light / Dark / System — the same data-theme the styleguide's own toggle drives.">
        <Specimen label="default"><ThemeSelectorDemo /></Specimen>
      </Section>

      <Section id="p7-shortcut" title="Keyboard-Shortcut Editor" desc="Rebindable shortcut list. Clicking the pencil enters capture mode; Escape cancels — itself fully keyboard-operable.">
        <Specimen label="default"><KeyboardShortcutEditor /></Specimen>
      </Section>

      <Section id="p7-provider" title="Provider/Model Configuration" desc="Grounded in the real config.get/config.set contract (ConfigStatus/ProviderInfo): pick a provider, edit the model id, provider re-derives from the model's prefix.">
        <Specimen label="default"><ProviderModelConfig /></Specimen>
      </Section>

      <Section id="p7-mcp" title="MCP Configuration" desc="Configured MCP servers with live connection status; forward-looking — no backend yet.">
        <Specimen label="default"><McpServerConfig /></Specimen>
      </Section>

      <Section id="p7-envvar" title="Environment-Variable Editor" desc="Key/value rows for workspace .env entries; secret-looking values mask like the API Key Input and never echo a stored value.">
        <Specimen label="default"><EnvironmentVariableEditor /></Specimen>
      </Section>

      <Section id="p7-apikey" title="API Key Input" desc="Security-sensitive: starts empty (a stored key is never returned by the platform), masked by default, reveal only shows what was just typed.">
        <Specimen label="key set"><ApiKeyInput keyVar="ANTHROPIC_API_KEY" present /></Specimen>
        <Specimen label="no key set"><ApiKeyInput keyVar="OPENAI_API_KEY" present={false} /></Specimen>
      </Section>
    </div>
  );
}
