# Phase 4A — Agents

The first slice of the AI-differentiating layer: components that represent the
five parallel analysts, the strategist, and the judge as first-class UI
objects — status, identity, confidence, capability, and the pipeline graph
that connects them. Built only from the token layer (semantic + component +
`--ai-*` AI-state tokens). Live gallery: `styleguide` → 4A · Agents.

Icons are local inline SVG (`viewBox 0 0 24 24`, `stroke currentColor`,
`stroke-width 1.75`, round caps) — the same Phosphor-style convention as
Phase 3A, redeclared per-file rather than shared.

---

## Status Badge

- **Purpose** — colour + glyph + label pill for an agent's lifecycle state:
  waiting, running, done, degraded, failed, awaiting-human.
- **Anatomy** — `p4a-status-badge` → `p4a-status-badge__dot` (running, animated)
  or `p4a-status-badge__icon` (all other states) + label text.
- **States** — `running` shows a pulsing dot instead of a static glyph; every
  other state shows a fixed glyph. Compact density shrinks height and padding.
- **Accessibility** — colour is never the only channel: each state pairs a hue
  with a distinct icon and a text label (WCAG 1.4.1). `running`'s pulse adds a
  third channel.
- **Tokens** — `--p4a-badge-fill`/`--p4a-badge-text` (set per status from
  `--ai-waiting`/`--ai-running`/`--ai-done`/`--ai-degraded`/`--ai-failed`/
  `--ai-awaiting-human` and their `-text` pairs), `--radius-pill`,
  `--text-caption`, `--dur-slow`.

## Agent Card

- **Purpose** — one agent in a selectable grid: avatar icon, name, role,
  description, status badge, inline confidence gauge.
- **When to use / not** — the agent picker / roster view. Not for a full
  profile — use Profile for that.
- **Anatomy** — `p4a-agent-card` (`role="option"`) → head (avatar +
  `StatusBadge`) + name/role/body text + foot (confidence track/fill/value, or
  an em-dash when no confidence yet).
- **States** — hover (surface + border shift), `aria-selected="true"`
  (accent border + tinted background), `:focus-visible` ring. Compact density
  shrinks padding and avatar size.
- **Keyboard** — `tabIndex={0}`, `Enter`/`Space` triggers selection.
- **Accessibility** — `role="option"` with `aria-selected`; selection state is
  not colour-only (border + background + the badge's own glyph/label).
- **Tokens** — `--card-pad/-bg/-border/-radius`, `--p4a-agent-color` (per-agent
  analyst colour, e.g. `--ai-analyst-customer`), `--avatar-md/-sm`,
  `--gauge-height/-track/-radius`, `--p4a-conf-fill` (one of
  `--ai-confidence-low/-medium/-high` by confidence tier), `--border-focus`.

## Profile

- **Purpose** — full agent detail panel: large avatar, name, role/position in
  the pipeline, description, status, and run stats (confidence, duration,
  tokens, cost).
- **When to use / not** — a focused single-agent view (e.g. an inspector
  panel). Not for the grid — use Agent Card there.
- **Anatomy** — `p4a-profile` → `p4a-profile__avatar` + body (head with
  name/role + `StatusBadge`, description paragraph, a stats row of
  value/label pairs).
- **Tokens** — `--avatar-lg/-md`, `--text-heading-4`, `--text-terminal`
  (tabular stat values), `--p4a-agent-color`, `--space-24/-12`.

## Capability List

- **Purpose** — the tools/data sources one agent can reach, each with an
  icon, name, short description, and a category tag.
- **Anatomy** — `p4a-cap-list` (`role="list"`) of `p4a-cap-item` rows: icon
  chip + name/description text + tag pill.
- **States** — item hover (border + background shift). Compact density
  shrinks padding and icon size.
- **Tokens** — `--p4a-cap-color` (per-capability, e.g. `--ai-thinking`,
  `--ai-tool`), `--surface-raised/-hover`, `--radius-control/-pill`.

## Selector

- **Purpose** — a searchable, multi-select listbox for choosing which agents
  participate in a run.
- **Anatomy** — `p4a-selector` (`role="listbox"`, `aria-multiselectable`) →
  search header (icon + `input[type=search]`) + `p4a-selector__list`
  (`role="group"`) of `p4a-selector__item` rows (icon, name, meta,
  check-on-select), or an empty state when the filter matches nothing.
- **States** — item hover, `aria-selected="true"` (accent border + tint),
  `:focus-visible` ring, empty-filter state.
- **Keyboard** — items are `tabIndex={0}`; `Enter`/`Space` toggles selection.
- **Accessibility** — `role="listbox"`/`role="option"` pairing with
  `aria-selected`; the filter input has its own `aria-label`.
- **Tokens** — `--surface-raised`, `--border-default/-subtle`, `--accent`,
  `--p4a-agent-color`, `--card-radius`.

## Timeline

- **Purpose** — vertical pipeline-execution log: one row per stage with a
  marker dot on a connecting rail, stage name, status badge, note, and
  start time / duration.
- **Anatomy** — `p4a-timeline` (`<ol>`) of `p4a-tl-row` — marker
  (`p4a-tl-marker`, pulsing dot when `data-live="true"`) on a vertical rail
  (`::before`), body (name + badge + note), meta (time + duration).
- **States** — the live row (`data-live="true"`) tints its marker amber via
  `--ai-running`. Compact density shrinks row height and rail offset.
- **Tokens** — `--p4a-tl-fill` (per-stage status colour), `--border-subtle`,
  `--ai-running`, `--text-terminal`-style tabular timing via
  `font-variant-numeric: tabular-nums`.

## Queue

- **Purpose** — the evaluation backlog: an ordered list of pending/running
  runs with rank, priority dot, title, model, status, and queued time.
- **Anatomy** — `p4a-queue` → `p4a-queue__head` (count + "Queued at" label) +
  `p4a-queue-item` rows (rank, priority dot, title/sub text, status badge,
  meta time).
- **States** — item hover, `aria-current="true"` (the in-flight run, tinted
  amber), `:focus-visible` ring.
- **Keyboard** — rows are focusable (`:focus-visible` styling implies
  `tabIndex`); each is a clickable list row.
- **Tokens** — `--p4a-priority-color` (`--ai-failed`/`--ai-degraded`/
  `--ai-waiting` for high/medium/low), `--ai-running`, `--surface-sunken/-raised`,
  `--border-subtle`.

## Dependency Graph

- **Purpose** — an SVG visualization of the LangGraph pipeline: analyst nodes
  fanning in to debate, recall feeding the strategist, the main spine through
  judge → risk → governance, with arrowed edges showing flow.
- **Anatomy** — `p4a-dep-graph` → inline `<svg>` (`role="img"`) of `p4a-edge`
  lines with arrowhead markers, `p4a-node` groups (`role="button"`,
  circle + optional pulsing dot + label), and a `p4a-graph-legend` (done /
  running / degraded / waiting / recall-path swatches).
- **Variants** — edge types: normal (solid `--ai-edge`), active (animated
  dash, `--ai-edge-active`), recall (dashed, `--ai-thinking`, lower opacity).
- **States** — node fill/stroke vary by status (`p4a-node--active/-done
  /-degraded/-failed`); the running node gets an extra pulsing dot.
- **Keyboard** — each node `<g>` is `tabIndex={0}` with a visible focus ring
  and an `aria-label` naming the stage and its status.
- **Accessibility** — the SVG has `role="img"` + `aria-label`; each node
  repeats its state as text via `aria-label`, not colour alone.
- **Tokens** — `--ai-edge`/`--ai-edge-active`, `--ai-node-border`/
  `-active-border`, `--ai-done/-degraded/-failed/-running` (+ `-text` pairs),
  `--ai-thinking`, `--surface-sunken/-raised`.

---

No new tokens are declared by `phase4a-agents.css` — it has no `:root` block.
All AI-state colour comes from the existing `--ai-*` semantic tokens; the
`--p4a-*` custom properties referenced above (badge fill/text, agent colour,
confidence fill, etc.) are per-instance values set inline via `style={}` in
the TSX, not entries in the token layer.
