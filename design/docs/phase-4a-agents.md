# Phase 4A — Agents

The first slice of the AI-differentiating layer: components that represent the
five parallel analysts, the strategist, and the judge as first-class UI
objects — status, identity, confidence, capability, and the pipeline graph
that connects them. Built only from the token layer (semantic + component +
`--ai-*` AI-state tokens). Live gallery: `styleguide` → 4A · Agents.

Icons are local inline SVG (`viewBox 0 0 24 24`, `stroke currentColor`,
`stroke-width 1.75`, round caps) — the same Phosphor-style convention as
Phase 3A, redeclared per-file rather than shared.

React API: not yet productized — each component here is a
`design/styleguide/src/phase4/` demo; a stable public API is defined when it
migrates to `desktop/src/ui/`.

---

## Status Badge

- **Purpose** — colour + glyph + label pill for an agent's lifecycle state:
  waiting, running, done, degraded, failed, awaiting-human.
- **When to use / not** — any place an agent/stage/run status needs a
  compact, reusable readout (Agent Card, Timeline, Queue, execution cards).
  Not for freeform status text — the label set is fixed to `STATUS_CFG`.
- **Anatomy** — `p4a-status-badge` → `p4a-status-badge__dot` (running, animated)
  or `p4a-status-badge__icon` (all other states) + label text.
- **Variants** — none; colour, icon, and label are entirely driven by the
  `status` prop (see States).
- **Sizes** — single size; compact density shrinks height and padding via
  `[data-density="compact"]`, not a size prop.
- **States** — `running` shows a pulsing dot instead of a static glyph; every
  other state shows a fixed glyph. Compact density shrinks height and padding.
- **Keyboard** — none; a static, non-interactive `span`.
- **Accessibility** — colour is never the only channel: each state pairs a hue
  with a distinct icon and a text label (WCAG 1.4.1). `running`'s pulse adds a
  third channel.
- **Content guidelines** — labels are the fixed set in `STATUS_CFG` ("Waiting",
  "Running", "Done", "Degraded", "Failed", "Awaiting human", "Cancelled") — not
  free text.
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
- **Variants** — none; colour comes from the agent's analyst identity
  (`--p4a-agent-color`), not a card variant.
- **Sizes** — single size; compact density shrinks the avatar to `--avatar-sm`
  and reduces padding (see States).
- **States** — hover (surface + border shift), `aria-selected="true"`
  (accent border + tinted background), `:focus-visible` ring. Compact density
  shrinks padding and avatar size.
- **Keyboard** — `tabIndex={0}`, `Enter`/`Space` triggers selection.
- **Accessibility** — `role="option"` with `aria-selected`; selection state is
  not colour-only (border + background + the badge's own glyph/label).
- **Content guidelines** — confidence renders as an em-dash, not "0%", when a
  score isn't available yet (e.g. a waiting analyst).
- **Implementation notes** — the confidence tier (low/medium/high →
  `--ai-confidence-*`) is thresholded at <50% and <75%, computed client-side
  from the raw `confidence` value.
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
- **Variants** — none; a single layout.
- **Sizes** — single size; compact density shrinks the avatar from
  `--avatar-lg` to `--avatar-md`.
- **States** — none interactive (a static display panel); the only state
  shown is the embedded `StatusBadge`'s.
- **Keyboard** — none; a static display panel, not focusable.
- **Accessibility** — the avatar icon is `aria-hidden` (decorative); the
  agent's live status is communicated only through the embedded `StatusBadge`,
  not the avatar or colour.
- **Content guidelines** — the stats row is a fixed set of four value/label
  pairs (Confidence, Duration, Tokens, Cost); values use tabular-numeral
  formatting via `--text-terminal`.
- **Tokens** — `--avatar-lg/-md`, `--text-heading-4`, `--text-terminal`
  (tabular stat values), `--p4a-agent-color`, `--space-24/-12`.

## Capability List

- **Purpose** — the tools/data sources one agent can reach, each with an
  icon, name, short description, and a category tag.
- **When to use / not** — an agent detail/inspector view showing the full set
  of tools/data sources an agent can reach; not for showing a single
  capability inline elsewhere.
- **Anatomy** — `p4a-cap-list` (`role="list"`) of `p4a-cap-item` rows: icon
  chip + name/description text + tag pill.
- **Variants** — none; item colour comes from the per-capability category
  (`--p4a-cap-color`), not a list variant.
- **Sizes** — single size; compact density shrinks item padding and icon size
  (see States).
- **States** — item hover (border + background shift). Compact density
  shrinks padding and icon size.
- **Keyboard** — none; a static list — items have no click handler or
  `tabIndex`.
- **Accessibility** — semantic `role="list"`; the category tag repeats as
  visible text, not colour alone.
- **Content guidelines** — name is a short capability title, description is
  one line, and tag is a short lowercase category word (e.g. "memory",
  "connector").
- **Tokens** — `--p4a-cap-color` (per-capability, e.g. `--ai-thinking`,
  `--ai-tool`), `--surface-raised/-hover`, `--radius-control/-pill`.

## Selector

- **Purpose** — a searchable, multi-select listbox for choosing which agents
  participate in a run.
- **When to use / not** — the agent picker for choosing which agents run
  next. Not for a single-select context — the listbox is inherently
  multi-select (`aria-multiselectable`).
- **Anatomy** — `p4a-selector` (`role="listbox"`, `aria-multiselectable`) →
  search header (icon + `input[type=search]`) + `p4a-selector__list`
  (`role="group"`) of `p4a-selector__item` rows (icon, name, meta,
  check-on-select), or an empty state when the filter matches nothing.
- **Variants** — none.
- **Sizes** — single size; compact density reduces the scrollable list's
  max-height (240px → 200px) and item padding.
- **States** — item hover, `aria-selected="true"` (accent border + tint),
  `:focus-visible` ring, empty-filter state.
- **Keyboard** — items are `tabIndex={0}`; `Enter`/`Space` toggles selection.
- **Accessibility** — `role="listbox"`/`role="option"` pairing with
  `aria-selected`; the filter input has its own `aria-label`.
- **Content guidelines** — search placeholder is "Filter agents…"; item meta
  is a short `·`-separated list of keywords (e.g. "feedback · issues · NPS").
- **Implementation notes** — the filter matches name or meta text,
  case-insensitively; toggling selection doesn't remove an item from the
  filtered list.
- **Tokens** — `--surface-raised`, `--border-default/-subtle`, `--accent`,
  `--p4a-agent-color`, `--card-radius`.

## Timeline

- **Purpose** — vertical pipeline-execution log: one row per stage with a
  marker dot on a connecting rail, stage name, status badge, note, and
  start time / duration.
- **When to use / not** — the detail view for one evaluation run's
  stage-by-stage history. Not for a multi-run overview — use Queue for that.
- **Anatomy** — `p4a-timeline` (`<ol>`) of `p4a-tl-row` — marker
  (`p4a-tl-marker`, pulsing dot when `data-live="true"`) on a vertical rail
  (`::before`), body (name + badge + note), meta (time + duration).
- **Variants** — none; row colour is entirely status-driven.
- **Sizes** — single size; compact density shrinks row height and rail
  offset (see States).
- **States** — the live row (`data-live="true"`) tints its marker amber via
  `--ai-running`. Compact density shrinks row height and rail offset.
- **Keyboard** — none; a read-only list, not focusable (contrast with Phase
  4B's interactive Execution Timeline, whose rows are expandable).
- **Accessibility** — semantic `<ol>`; each marker carries an `aria-label`
  naming the stage and its status text, not colour alone.
- **Content guidelines** — note is a short one-line status summary; time and
  duration show an em dash for stages that haven't started.
- **Tokens** — `--p4a-tl-fill` (per-stage status colour), `--border-subtle`,
  `--ai-running`, `--text-terminal`-style tabular timing via
  `font-variant-numeric: tabular-nums`.

## Queue

- **Purpose** — the evaluation backlog: an ordered list of pending/running
  runs with rank, priority dot, title, model, status, and queued time.
- **When to use / not** — the evaluation backlog across multiple initiatives.
  Not for a single run's stage progress — use Timeline for that.
- **Anatomy** — `p4a-queue` → `p4a-queue__head` (count + "Queued at" label) +
  `p4a-queue-item` rows (rank, priority dot, title/sub text, status badge,
  meta time).
- **Variants** — none; row colour is driven by priority (see Tokens).
- **Sizes** — single size; compact density reduces item padding.
- **States** — item hover, `aria-current="true"` (the in-flight run, tinted
  amber), `:focus-visible` ring.
- **Keyboard** — rows are focusable (`:focus-visible` styling implies
  `tabIndex`); each is a clickable list row.
- **Accessibility** — `role="list"`/`role="listitem"` semantics; the
  priority dot carries its own `aria-label` (e.g. "high priority") so
  priority is never colour-only; the in-flight run uses `aria-current="true"`.
- **Content guidelines** — title truncates with an ellipsis on overflow; sub
  text is the model id.
- **Tokens** — `--p4a-priority-color` (`--ai-failed`/`--ai-degraded`/
  `--ai-waiting` for high/medium/low), `--ai-running`, `--surface-sunken/-raised`,
  `--border-subtle`.

## Dependency Graph

- **Purpose** — an SVG visualization of the LangGraph pipeline: analyst nodes
  fanning in to debate, recall feeding the strategist, the main spine through
  judge → risk → governance, with arrowed edges showing flow.
- **When to use / not** — an overview of the pipeline topology and the
  current run's position within it. Not for step-by-step stage detail — use
  Timeline for that.
- **Anatomy** — `p4a-dep-graph` → inline `<svg>` (`role="img"`) of `p4a-edge`
  lines with arrowhead markers, `p4a-node` groups (`role="button"`,
  circle + optional pulsing dot + label), and a `p4a-graph-legend` (done /
  running / degraded / waiting / recall-path swatches).
- **Variants** — edge types: normal (solid `--ai-edge`), active (animated
  dash, `--ai-edge-active`), recall (dashed, `--ai-thinking`, lower opacity).
- **Sizes** — single size; compact density scales the whole SVG to 90%.
- **States** — node fill/stroke vary by status (`p4a-node--active/-done
  /-degraded/-failed`); the running node gets an extra pulsing dot.
- **Keyboard** — each node `<g>` is `tabIndex={0}` with a visible focus ring
  and an `aria-label` naming the stage and its status.
- **Accessibility** — the SVG has `role="img"` + `aria-label`; each node
  repeats its state as text via `aria-label`, not colour alone.
- **Content guidelines** — node labels are short, one-word stage/analyst
  names (e.g. "Customer", "Judge") centered below the node; the SVG doesn't
  wrap or truncate longer labels.
- **Implementation notes** — edges are computed as straight lines trimmed by
  each node's radius (plus extra gap for the arrowhead), not routed or
  curved; three `<marker>` defs supply the arrowhead per edge type
  (normal/active/recall).
- **Tokens** — `--ai-edge`/`--ai-edge-active`, `--ai-node-border`/
  `-active-border`, `--ai-done/-degraded/-failed/-running` (+ `-text` pairs),
  `--ai-thinking`, `--surface-sunken/-raised`.

---

No new tokens are declared by `phase4a-agents.css` — it has no `:root` block.
All AI-state colour comes from the existing `--ai-*` semantic tokens; the
`--p4a-*` custom properties referenced above (badge fill/text, agent colour,
confidence fill, etc.) are per-instance values set inline via `style={}` in
the TSX, not entries in the token layer.
