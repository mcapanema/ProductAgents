# Phase 7 — Settings components

Configuration surfaces: navigating settings, grouping related preferences,
switching theme, rebinding keyboard shortcuts, choosing a model provider,
wiring MCP servers, editing environment variables, and the one
security-sensitive control — an API key. Provider/Model Configuration and API
Key Input are grounded in the real `config.get`/`config.set` IPC contract
(`ConfigStatus`/`ProviderInfo`, `desktop/src/ipc/types.ts`) that
`desktop/src/panels/SettingsPanel.tsx` already exercises; Theme Selector,
Keyboard-Shortcut Editor, MCP Configuration, and the Environment-Variable
Editor have no backend yet — forward-looking, the same posture as Phase 6's
git/file-tree state. Built only from the existing token layer (no new
colors). Live gallery: `styleguide` → Settings.

Icons are inline SVG (`viewBox 0 0 24 24`, `stroke currentColor`,
`stroke-width 1.75`, round caps), defined locally in `Phase7Settings.tsx`.
Status hues reuse `--success`/`--danger`/`--info`/`--signal` (amber is a
generic *state* token, never a literal `--warning`) — never color alone, every
state pairs an icon with a text label.

**Security posture (API Key Input + secret rows in the Environment-Variable
Editor):** the platform never echoes a stored secret back to the GUI, so
these components never hold one in state either — the field starts empty, a
placeholder communicates "a value is set", and the reveal toggle only shows
what the user just typed (disabled while the field is empty).

---

## Settings Navigation

- **Purpose** — the settings sidebar: one entry per resource, active item
  marked.
- **When to use / not** — the left rail of a settings page. Not a generic
  app-wide nav — see Phase 3B for that.
- **Anatomy** — `p7-nav` list of `p7-nav__item` buttons (icon + label).
  Demonstrated composed with Section into a full settings-page layout
  (`p7-shell`: nav + body, swapping body content per selection).
- **States** — `aria-current="page"` on the active item paints it with
  `--accent-subtle`/`--accent-text`.
- **Keyboard** — every item is a real `button` in normal tab order.
- **Tokens** — `--control-md`, `--radius-control`, `--accent-subtle`,
  `--accent-text`, `--focus-ring-width/-offset`, `--border-focus`.

## Section

- **Purpose** — a titled, divided group within a settings page: heading,
  optional description, body.
- **When to use / not** — grouping related Preference Cards or a
  configuration block. Not the gallery's own `Section` (styleguide chrome,
  `sg.tsx`) — this is a product component, named `SettingsSection` in code to
  avoid the collision.
- **Anatomy** — `p7-section__head` (title + description) over a
  `--border-subtle` divider, then `p7-section__body`.
- **Tokens** — `--text-heading-4`, `--text-body-s`, `--text-tertiary`,
  `--border-subtle`.

## Preference Card

- **Purpose** — a labelled setting row pairing a description with its
  control.
- **When to use / not** — inside a Section body. Not a generic list row —
  it always has a label + control pair.
- **Anatomy** — `p7-pref` → `p7-pref__meta` (label + description) +
  `p7-pref__control` (a `Switch`, a `select`, or a composed control like
  Theme Selector).
- **States** — `Switch` is `role="switch"` with `aria-checked`, track color
  flips `--surface-pressed` → `--accent`.
- **Keyboard** — `Switch` is a real `button`; toggled with Enter/Space like
  any button.
- **Tokens** — `--card-bg/-border/-radius`, `--space-48/-20/-4` (switch
  geometry), `--accent`, `--surface-pressed`, `--surface-raised`.

## Theme Selector

- **Purpose** — three-way choice: Light / Dark / System.
- **When to use / not** — an Appearance preference. The same `data-theme`
  values the styleguide's own toggle drives, so the choice is grounded in a
  real mechanism even though no settings-page backend exists yet.
- **Anatomy** — `p7-theme` (`role="radiogroup"`) of `p7-theme__opt`
  (`role="radio"`) buttons, each with an icon (sun/moon/monitor) + label.
- **States** — the active option gets a raised `--card-bg-raised` chip with
  `--card-shadow`.
- **Keyboard** — real buttons with `aria-checked`; operable via Tab + Enter
  (a future iteration could add roving-tabindex arrow-key navigation for full
  `radiogroup` conformance).
- **Tokens** — `--surface-sunken`, `--card-bg-raised`, `--card-shadow`,
  `--radius-control`.

## Keyboard-Shortcut Editor

- **Purpose** — view and rebind shortcut bindings.
- **When to use / not** — a Keyboard settings section. Not a one-off
  shortcut hint — see the Command Palette (Phase 3B) for that.
- **Anatomy** — `p7-shortcut-list` of `p7-shortcut-row` (action label +
  `p7-kbd` chips, or a capture placeholder while recording, + an edit/cancel
  pencil button).
- **States** — `default` (keys shown) vs `recording` ("Press a key… (Esc to
  cancel)", `--text-warning`).
- **Keyboard** — every row's pencil is a real `button`; `Escape` cancels an
  in-progress capture — the component demonstrates the product's own
  keyboard-first constraint.
- **Tokens** — `--text-warning`, `--text-code`, `--card-bg-raised`,
  `--card-border`, `--card-shadow`.

## Provider/Model Configuration

- **Purpose** — pick a model provider and edit the model id.
- **When to use / not** — the Providers & Models settings section. Grounded
  in the real shape `desktop/src/panels/SettingsPanel.tsx` already writes via
  `config.set` (`ProviderInfo[]` → provider `select`, `model` text input);
  mirrors that panel's "provider is derived from the model's prefix when
  present" logic in the hint line.
- **Anatomy** — `p7-field` × 2 (Provider `select`, Model `input`) + a
  `p7-hint` line.
- **Tokens** — `--field-bg/-border/-text/-height/-radius`, `--text-label`,
  `--text-code`.

## MCP Configuration

- **Purpose** — list configured MCP servers with live connection status; add
  new ones.
- **When to use / not** — an MCP Servers settings section. Forward-looking:
  no `config.get`/`config.set` shape exists for this yet.
- **Anatomy** — `p7-mcp-list` of `p7-mcp-row` (plug icon, name + command,
  status chip, remove button) + an `Add MCP server` dashed row.
- **States** — `connected` (success), `error` (danger), `disconnected`
  (signal/amber) — each pairs an icon (`check-circle`/`x-circle`/
  `alert-triangle`) with a text label, never color alone.
- **Tokens** — `--text-success`, `--text-error`, `--text-warning`,
  `--card-bg/-border/-radius`.

## Environment-Variable Editor

- **Purpose** — edit a workspace's `.env`-style key/value pairs.
- **When to use / not** — an Environment settings section. Forward-looking,
  same posture as MCP Configuration.
- **Anatomy** — `p7-envvar-list` of `p7-envvar-row` (key input, value input,
  optional reveal toggle, remove button) + an `Add variable` dashed row.
- **States** — secret-looking rows (`secret: true`) render as `password`
  inputs, start empty with a "stored — leave blank to keep" placeholder, and
  add a reveal toggle that is disabled while the field is empty — the same
  contract as API Key Input, not a separate masking scheme.
- **Tokens** — `--field-*` (shared with all text inputs in this phase),
  `--state-disabled-opacity/-cursor`.

## API Key Input

- **Purpose** — the one security-sensitive settings control: enter or
  replace a provider's API key.
- **When to use / not** — paired with Provider/Model Configuration. Never
  reused for a non-secret field — see the plain `p7-field` pattern for those.
- **Anatomy** — `p7-field` (label + `(key_var)` hint) → `p7-apikey__row`
  (password `input` + reveal `p7-icon-btn`) → a presence status line.
- **States** — `present` (success: "Key present") vs not (warning: "No key
  set"); the input itself never distinguishes "has a stored key" beyond the
  placeholder text, exactly mirroring `SettingsPanel.tsx`'s
  `status.key_present` contract.
- **Security** — `value` starts as `""` every render (the platform never
  returns a stored key); the reveal button is `disabled` while `value === ""`
  so there is never a stored secret to accidentally expose, only what the
  user is actively typing; `autoComplete="off"`.
- **Tokens** — `--text-success`, `--text-warning`, `--field-*`,
  `--state-disabled-opacity/-cursor`.
