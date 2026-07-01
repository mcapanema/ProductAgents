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

React API: not yet productized — each component here is a
`design/styleguide/src/phase7/` demo; a stable public API is defined when it
migrates to `desktop/src/ui/`.

---

## Settings Navigation

- **Purpose** — the settings sidebar: one entry per resource, active item
  marked.
- **When to use / not** — the left rail of a settings page. Not a generic
  app-wide nav — see Phase 3B for that.
- **Anatomy** — `p7-nav` list of `p7-nav__item` buttons (icon + label).
  Demonstrated composed with Section into a full settings-page layout
  (`p7-shell`: nav + body, swapping body content per selection).
- **Variants** — none; a single list-of-buttons pattern.
- **Sizes** — single size (`--control-md` item height); no compact-density
  override defined on the nav itself (the composed demo's shell body,
  `p7-shell__body`, does shrink in compact — that's Section's shell).
- **States** — `aria-current="page"` on the active item paints it with
  `--accent-subtle`/`--accent-text`.
- **Accessibility** — `<nav aria-label="Settings sections">` wraps a real
  `<ul>`/`<button>` list; the current item is exposed to assistive tech via
  `aria-current="page"` (see States).
- **Keyboard** — every item is a real `button` in normal tab order.
- **Content guidelines** — one short (1–2 word) label per entry, paired
  with a single representative icon; no counts or badges on the item.
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
- **Variants** — none; a single heading + optional-description + body
  layout.
- **Sizes** — single size; no compact-density override defined.
- **States** — none; a static, non-interactive wrapper.
- **Accessibility** — semantic `<h4>` title over an optional `<p>`
  description; no ARIA role beyond default heading semantics.
- **Keyboard** — none; not interactive.
- **Content guidelines** — `title` is required; `description` is optional,
  one sentence stating the group's scope.
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
- **Variants** — none; the row shape is fixed — only the control content
  varies (`Switch`, a `select`, or a composed control like Theme Selector).
- **Sizes** — single size; compact density reduces card padding
  (`--space-12` → `--space-8`, see `[data-density="compact"] .p7-pref`).
- **States** — `Switch` is `role="switch"` with `aria-checked`, track color
  flips `--surface-pressed` → `--accent`.
- **Accessibility** — `Switch` carries an `aria-label` matching the
  preference's visible label (no `<label for>` association — the label
  text sits in a plain `span`, not a `<label>`); a `select` control carries
  its own `aria-label` via the shared `Select` helper.
- **Keyboard** — `Switch` is a real `button`; toggled with Enter/Space like
  any button.
- **Content guidelines** — description (optional) states a scope or
  consequence, not a restatement of the label, e.g. "No initiative text or
  evidence ever leaves the machine."
- **Tokens** — `--card-bg/-border/-radius`, `--space-48/-20/-4` (switch
  geometry), `--accent`, `--surface-pressed`, `--surface-raised`.

## Theme Selector

- **Purpose** — three-way choice: Light / Dark / System.
- **When to use / not** — an Appearance preference. The same `data-theme`
  values the styleguide's own toggle drives, so the choice is grounded in a
  real mechanism even though no settings-page backend exists yet.
- **Anatomy** — `p7-theme` (`role="radiogroup"`) of `p7-theme__opt`
  (`role="radio"`) buttons, each with an icon (sun/moon/monitor) + label.
- **Variants** — none; always the fixed Light/Dark/System three-way set.
- **Sizes** — single size (`--control-sm` option height); no
  compact-density override defined.
- **States** — the active option gets a raised `--card-bg-raised` chip with
  `--card-shadow`.
- **Accessibility** — group carries `aria-label="Theme"`; each option's
  accessible name is its visible label text (the icon is `aria-hidden`).
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
- **Variants** — none; one row layout for every shortcut.
- **Sizes** — single size; no compact-density override defined.
- **States** — `default` (keys shown) vs `recording` ("Press a key… (Esc to
  cancel)", `--text-warning`).
- **Accessibility** — the capture placeholder is `role="status"` (announces
  "Press a key… (Esc to cancel)" to assistive tech when recording starts);
  the pencil button's `aria-label` swaps between "Edit shortcut for
  {action}" and "Cancel editing {action}".
- **Keyboard** — every row's pencil is a real `button`; `Escape` cancels an
  in-progress capture — the component demonstrates the product's own
  keyboard-first constraint.
- **Content guidelines** — action labels are short imperative phrases
  ("Open command palette"); key chips render exactly what was pressed
  (single characters upper-cased, Space spelled out).
- **Implementation notes** — capture listens at the list level via a bubble-
  phase `onKeyDown` (the handler is named `onKeyDownCapture`, but nothing
  binds the capture-phase prop), not per-row, so any keydown from a focused
  row descendant reaches it while `recording`, since nothing stops
  propagation in between; a bare
  modifier press (Cmd/Ctrl/Alt/Shift alone) doesn't complete a binding —
  `describeKeyCombo` returns `null` and capture keeps waiting for the
  following non-modifier key.
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
- **Variants** — none; two fixed fields (Provider `select` + Model
  `input`).
- **Sizes** — single size; container capped at `max-width: 420px`
  (`.p7-provider`).
- **States** — standard field hover/focus (`--field-border-hover/-focus`);
  no dedicated disabled/error/loading state modeled here.
- **Accessibility** — both fields sit inside a native `<label>` (implicit
  text association) plus a redundant `aria-label` on the underlying
  `select`/`input`.
- **Keyboard** — native `select` and `input`; standard Tab order, no custom
  handling.
- **Content guidelines** — the hint line always names the exact env var
  (`PRODUCTAGENTS_MODEL`) and interpolates the live provider id in the
  prefix example.
- **Implementation notes** — selecting a Provider resets Model to that
  provider's `default_model` (`onProviderChange`) — a seed, not the source
  of truth: the actual runtime provider is derived from the model id's own
  prefix when present (see the hint line). The `select` uses `appearance:
  none` with a decorative caret `Icon` standing in for the native arrow —
  `appearance: auto` fights the field's own padding/height box model (same
  technique as Phase 3C's `fm-select`).
- **Tokens** — `--field-bg/-border/-text/-height/-radius`, `--text-label`,
  `--text-code`.

## MCP Configuration

- **Purpose** — list configured MCP servers with live connection status; add
  new ones.
- **When to use / not** — an MCP Servers settings section. Forward-looking:
  no `config.get`/`config.set` shape exists for this yet.
- **Anatomy** — `p7-mcp-list` of `p7-mcp-row` (plug icon, name + command,
  status chip, remove button) + an `Add MCP server` dashed row.
- **Variants** — none; one row layout, only the status value varies (see
  States).
- **Sizes** — single size; compact density reduces row padding
  (`--space-12` → `--space-8`, see `[data-density="compact"] .p7-mcp-row`).
- **States** — `connected` (success), `error` (danger), `disconnected`
  (signal/amber) — each pairs an icon (`check-circle`/`x-circle`/
  `alert-triangle`) with a text label, never color alone.
- **Accessibility** — status icons are decorative (`aria-hidden`; the
  adjacent text label carries the meaning); the remove button's
  `aria-label` is `Remove {name}` per row.
- **Keyboard** — remove buttons and the `Add MCP server` row are real
  buttons in normal tab order.
- **Content guidelines** — commands can be long full CLI invocations; the
  row truncates them with an ellipsis (`p7-mcp-row__cmd`), so the full
  command isn't visible without widening the layout.
- **Tokens** — `--text-success`, `--text-error`, `--text-warning`,
  `--card-bg/-border/-radius`.

## Environment-Variable Editor

- **Purpose** — edit a workspace's `.env`-style key/value pairs.
- **When to use / not** — an Environment settings section. Forward-looking,
  same posture as MCP Configuration.
- **Anatomy** — `p7-envvar-list` of `p7-envvar-row` (key input, value input,
  optional reveal toggle, remove button) + an `Add variable` dashed row.
- **Variants** — none; one row layout — only `secret` toggles password
  masking (see States).
- **Sizes** — single size; row is a 4-column grid (`1fr 1fr auto auto` —
  key, value, reveal, remove) that fills the available width; no
  compact-density override defined.
- **States** — secret-looking rows (`secret: true`) render as `password`
  inputs, start empty with a "stored — leave blank to keep" placeholder, and
  add a reveal toggle that is disabled while the field is empty — the same
  contract as API Key Input, not a separate masking scheme.
- **Accessibility** — each input carries an `aria-label` (`"variable
  name"` / `"value for {key}"`, no visible `<label>`); reveal and remove
  buttons get per-row `aria-label`s (`Reveal value` / `Hide value`,
  `Remove {key}`).
- **Keyboard** — every input and button (reveal, remove, add) is a native
  or real element in normal tab order; no custom handling.
- **Content guidelines** — the secret placeholder text
  (`"•••••••• (set — leave blank to keep)"`) is identical to API Key
  Input's, deliberately, per the shared contract; non-secret rows show no
  placeholder.
- **Tokens** — `--field-*` (shared with all text inputs in this phase),
  `--state-disabled-opacity/-cursor`.

## API Key Input

- **Purpose** — the one security-sensitive settings control: enter or
  replace a provider's API key.
- **When to use / not** — paired with Provider/Model Configuration. Never
  reused for a non-secret field — see the plain `p7-field` pattern for those.
- **Anatomy** — `p7-field` (label + `(key_var)` hint) → `p7-apikey__row`
  (password `input` + reveal `p7-icon-btn`) → a presence status line.
- **Variants** — none; a single layout.
- **Sizes** — single size; container capped at `max-width: 420px`
  (`.p7-apikey`).
- **States** — `present` (success: "Key present") vs not (warning: "No key
  set"); the input itself never distinguishes "has a stored key" beyond the
  placeholder text, exactly mirroring `SettingsPanel.tsx`'s
  `status.key_present` contract.
- **Security** — `value` starts as `""` every render (the platform never
  returns a stored key); the reveal button is `disabled` while `value === ""`
  so there is never a stored secret to accidentally expose, only what the
  user is actively typing; `autoComplete="off"`.
- **Accessibility** — the visible label and the input row both sit inside
  one `<label>` (the input carries a redundant `aria-label="api key"`); the
  reveal button's `aria-label` swaps "Reveal key"/"Hide key" to match state.
- **Keyboard** — native password `input` (Tab to focus, standard text
  editing) plus a real reveal `button`; Tab order is input → reveal button.
- **Content guidelines** — placeholder differs by presence: `"required"`
  when no key is set vs `"•••••••• (set — leave blank to keep)"` when one
  is.
- **Do's and don'ts** — never seed `value` from a fetched or stored key,
  even a masked one — the platform doesn't return one, and doing so would
  defeat the empty-start contract this control exists to enforce (see
  Security).
- **Tokens** — `--text-success`, `--text-warning`, `--field-*`,
  `--state-disabled-opacity/-cursor`.
