# Phase 8 — Monitoring & observability

Event Timeline, Metrics Card, Resource/Memory/Token Usage, Execution Statistics,
Cost Dashboard, Performance Graph, Health Indicator, across
`src/phase8/Phase8Monitoring.tsx` + `phase8-monitoring.css`, prefixed `p8-`.
Live gallery: `styleguide` → Monitoring.

**Grounding.** Event Timeline, Execution Statistics, Performance Graph, and
Health Indicator are grounded in real platform shapes: the full
`productagents.platform.events.Event` taxonomy (`SessionStarted`,
`NodeProgress`, `AnalystCompleted`, `DebateTurnEmitted`, `RiskAssessed`,
`Judged`, `GovernanceAdvised`, `ApprovalRequested`, `FinalVerdict`,
`NodeFailed`, `SessionFailed`, `SessionCancelled`, `SessionFinished`) plus
`Session.id`/`workflow`/`status`/`created_at`, as returned by
`SessionService.events()`/`.list()` over the Event Store. Latency in
Execution Statistics and Performance Graph is computed from the real `ts`
deltas between consecutive events — the only timing signal the Event Store
persists today. Resource/Memory/Token Usage and Cost Dashboard have no
backend schema yet (no token/memory/cost tracking exists anywhere in the
platform) — forward-looking, sized to the same `--gauge-*` tokens Phase 4C's
per-call Token Usage Bar already uses, and keyed off the same node
identifiers the real event vocabulary uses, so wiring is additive once a
metrics source lands (the same posture Phase 6 took for git/file-tree state).

Built only from the existing token layer (no new colors — `contrast.py` still
0 failures, both themes + CVD); reuses the `--timeline-*` and `--gauge-*`
component tokens Phase 2 reserved for exactly this (their first real
consumer). Icons are inline SVG (`viewBox 0 0 24 24`, `stroke currentColor`,
`stroke-width 1.75`, round caps), defined locally in `Phase8Monitoring.tsx`.

React API: not yet productized — each component here is a
`design/styleguide/src/phase8/` demo; a stable public API is defined when it
migrates to `desktop/src/ui/`.

---

## Event Timeline

- **Purpose** — the persisted, full-fidelity log of one session's Event
  Store rows: every `Event` subclass, seq-ordered, for after-the-fact audit.
- **When to use / not** — a session detail/audit view (past or current run).
  Not the live in-flight pipeline view — that's Phase 4B's Execution
  Timeline, which shows the streaming run replacing the raw-JSON dump.
- **Anatomy** — `p8-timeline` (`<ol>`) → `p8-timeline__row` per event: a
  rail-connected node (icon, tinted by event kind) + label + timestamp +
  optional detail line.
- **Variants** — none; a single list/row shape. The 13 event kinds vary
  icon + tone only (see States).
- **Sizes** — single size; node diameter is `--timeline-node-size`, row
  spacing `--timeline-row-gap` — overall row height follows content (label +
  optional detail).
- **States** — one visual per event kind (13 total), each pairing a distinct
  icon with a token-driven tone — never color alone.
- **Accessibility** — `aria-label="Session event log"` on the list; every
  row carries a real text label, not just a colored dot.
- **Keyboard** — none; a static, non-interactive `<ol>` — no row is
  focusable.
- **Content guidelines** — `label` is a short human-readable rendering of the
  event dataclass's real fields (node, round/side, level, passed, verdict,
  ...); `detail` is optional and one line, only present when the event
  carries extra context (e.g. a debate rebuttal, a judge verdict summary).
- **Implementation notes** — each row sets `--p8-tl-color` inline (drives the
  node's icon color + border) from `EVENT_META`, so a new `EventKind` needs
  no new CSS; the connector line between rows is a fixed `--timeline-rail`
  tint, independent of event kind.
- **Tokens** — `--timeline-rail`, `--timeline-node-size`, `--timeline-row-gap`,
  `--timeline-connector-width`, `--ai-running`/`--ai-done`/`--ai-advocate`/
  `--signal`/`--accent`/`--ai-awaiting-human`/`--ai-failed`/`--danger`/
  `--success`/`--text-tertiary`, `--surface-raised`, `--text-code` (timestamp).

## Metrics Card

- **Purpose** — a threshold-tiered stat tile (ok/warning/critical/neutral)
  for monitoring values that need a status read, not just an up/down delta.
- **When to use / not** — dashboards where a value can cross a threshold
  (failed-session counts, pass rates). For a plain value+delta metric with no
  threshold concept, use Phase 3D's Stat Card directly — this does not
  replace it.
- **Anatomy** — `p8-metric` → head (icon + label), big value, foot (tier word
  + optional delta with trend icon).
- **Variants** — none; one tile shape. The trend delta (icon + %) is present
  only when `deltaPct` is passed.
- **Sizes** — single size; tiles size via the `p8-grid`
  `auto-fill, minmax(180px, 1fr)` layout, not the tile itself.
- **States** — `data-tier="ok"|"warning"|"critical"|"neutral"`; critical/
  warning additionally tint the card border.
- **Accessibility** — tier is a text word (`Normal`/`Elevated`/`Critical`)
  alongside color, and delta direction pairs a trend icon with the %.
- **Keyboard** — none; a static, non-interactive tile.
- **Content guidelines** — label renders uppercase via CSS
  (`text-transform: uppercase`; author it in normal case); the foot always
  shows the tier word, never a bare percentage.
- **Implementation notes** — critical/warning border tint
  (`--border-error`/`--border-warning`) is applied via the `data-tier`
  attribute in CSS, while the tier word's color is set inline via
  `--p8-tier-color` from `TIER_META` — two mechanisms for the same tier
  value.
- **Tokens** — `--card-bg/-border/-radius/-pad`, `--text-heading-3`,
  `--text-caption`, `--ls-wide`, `--text-success/-warning/-error`,
  `--border-error/-warning`.

## Resource / Memory / Token Usage

- **Purpose** — a session-aggregate usage gauge (context tokens, memory,
  vector store, ...): a track/fill bar plus a `used / total` reading.
- **When to use / not** — session-level totals. For a single LLM call's
  context-window usage, use Phase 4C's Token Usage Bar instead — this is the
  aggregate counterpart, not a replacement.
- **Anatomy** — `p8-usage` → head (icon + label, `used / total unit`
  reading), `p8-usage__track` (`role="progressbar"`), tier line below.
- **Variants** — none; one gauge shape. `unit` is a free string
  (`tok`/`MB`/...) set per instance.
- **Sizes** — single size; track height fixed by `--gauge-height`, gauge
  width comes from the `p8-stack` container (max 420px), not the gauge
  itself.
- **States** — tier computed from percentage: ok (<70%), warning (70–90%),
  critical (>90%); each tier recolors the fill and the percentage text.
- **Accessibility** — `role="progressbar"` with `aria-valuenow/-min/-max`;
  the tier word is always printed as text, never color-only.
- **Keyboard** — none; `role="progressbar"` is a static readout, not a
  focusable widget.
- **Content guidelines** — reading is `used / total unit`, both numbers
  passed through `toLocaleString()` for thousands separators.
- **Implementation notes** — percentage is clamped to 100
  (`Math.min(100, ...)`), so `used > total` can't overflow the fill past the
  track.
- **Tokens** — `--gauge-height`, `--gauge-radius`, `--gauge-track`,
  `--success`/`--signal`/`--danger`, `--text-warning`/`--text-error`.

## Execution Statistics

- **Purpose** — aggregate counts for one session: total events, distinct
  nodes touched, average inter-event latency, debate turns.
- **When to use / not** — a session summary header. Computed entirely from
  the same Event Store rows the Event Timeline renders — not a separate data
  source.
- **Anatomy** — a `p8-grid` of Metric Cards (reuses that component directly).
- **Variants** — none; one grid of Metric Cards — see Metrics Card for its
  own variants.
- **Sizes** — single size; inherits the `p8-grid` layout (see Metrics Card).
- **States** — latency tier flips to `warning` above a 20s average.
- **Accessibility** — inherits Metric Card's per-tile accessibility (see
  above); no additional ARIA at the grid level.
- **Keyboard** — none; a static, non-interactive grid.
- **Content guidelines** — tile labels are short noun phrases ("Total
  events", "Nodes touched", "Avg event latency", "Debate turns").
- **Implementation notes** — "Nodes touched" counts distinct *event labels*
  from `node_progress`/`analyst_completed` rows, not distinct node ids; a
  node that both starts and completes (as in the sample data) produces two
  different label strings ("X running" / "X completed"), so the tile can
  over-count nodes touched until it's wired to a real per-node id.
- **Tokens** — see Metrics Card.

## Cost Dashboard

- **Purpose** — per-node $ breakdown for one session plus a running total.
- **When to use / not** — forward-looking: no cost schema exists anywhere in
  the platform today. Keyed off the same node identifiers
  (`customer_research`, `market`, `debate`, ...) the real event vocabulary
  already uses, so a future cost source can populate it without a reshape.
- **Anatomy** — `p8-cost` → total (icon + $ figure), `p8-cost__list` of rows
  (node name, proportional bar, $ amount).
- **Variants** — none; one list shape.
- **Sizes** — single size; `p8-cost` caps at 420px wide.
- **States** — none; a static, non-interactive breakdown.
- **Accessibility** — every bar has an adjacent numeric $ label; the bar
  alone never carries the value.
- **Keyboard** — none; a static, non-interactive list.
- **Content guidelines** — node identifiers are the real event-vocabulary
  keys (`customer_research`, `market`, `debate`, ...), rendered in monospace
  (`--text-code`); `.p8-cost__node` truncates overflow with an ellipsis and
  no `title` fallback, so keep identifiers short.
- **Implementation notes** — if `lines` sum to $0, the per-row bar-fill
  percentage divides by zero (`NaN%`) — callers should guard against an
  all-zero cost breakdown.
- **Tokens** — `--card-bg/-border/-radius/-pad`, `--text-heading-2`,
  `--gauge-height/-radius/-track`, `--accent`, `--text-code`.

## Performance Graph

- **Purpose** — inter-event latency across a session's sequence, plotted
  from the same real `ts` deltas Execution Statistics summarizes.
- **When to use / not** — a session's timing trend. Not a generic
  sparkline — Phase 3D's `Sparkline` stays the tiny, decorative,
  `aria-hidden` trend glyph used inside a Stat Card; this is a full chart
  with axes/legend/tooltips for a dedicated reading.
- **Anatomy** — `p8-perf` → legend, inline SVG line chart (gridlines, axis
  labels, focusable per-point circles with `<title>` tooltips), a
  `<details>` "View as table" disclosure with the same data as a real
  `<table>`.
- **Variants** — none; one chart shape.
- **Sizes** — single size; 480×140 SVG `viewBox` scales to its container via
  `width: 100%`, no compact-density override defined.
- **States** — none beyond per-point focus and the table disclosure's
  open/closed toggle — see Keyboard.
- **Accessibility** — `role="img"` with an `aria-label` summary sentence on
  the SVG (so a screen reader gets the trend without parsing the chart);
  every point is keyboard-focusable; the table disclosure is the WCAG
  text-alternative for the data itself, not just a caption.
- **Keyboard** — each point is a real focusable element (`tabIndex={0}`) in
  seq order, carrying an `aria-label` + `<title>` tooltip; the "View as
  table" `<summary>` is natively focusable and toggles on Enter/Space.
- **Content guidelines** — the SVG's `aria-label` summary sentence is
  generated from the same latency data (min/max/avg) — don't hand-author
  duplicate copy that could drift from it.
- **Implementation notes** — needs at least 2 event gaps (3+ events) to
  render correctly; with exactly 1 gap, `stepX` divides by zero and the
  single point's x-coordinate becomes `NaN`.
- **Tokens** — `--border-subtle` (gridlines), `--text-tertiary` (axis),
  `--accent` (line/points), `--surface-default` (point stroke),
  `--border-focus`, `--focus-ring-width/-offset`, `--text-link`.

## Health Indicator

- **Purpose** — a compact status badge (dot + icon + subject + word) for a
  monitored subject's current health.
- **When to use / not** — keyed off `Session.status` plus whether a
  `NodeFailed`/`SessionFailed`/`SessionCancelled` occurred along the way.
  Generalizes Phase 6's `p6-health`, which is GitHub-connector-specific
  (healthy/degraded/error only); for a connector's health specifically,
  prefer Phase 6's Repository Card.
- **Anatomy** — `p8-health` → colored dot, status icon, subject name, status
  word.
- **Variants** — none; one badge shape across all six states.
- **Sizes** — single size; no compact-density override defined.
- **States** — `healthy`/`degraded`/`error`/`running`/`idle`/`unknown`, six
  total (three more than Phase 6's connector-scoped set).
- **Accessibility** — state is never color-only: dot + icon + text word all
  carry it independently.
- **Keyboard** — none; a static, non-interactive `<span>`.
- **Content guidelines** — `subject` is free text (a session/workflow
  name); `word` is fixed vocabulary per state (Healthy/Degraded/Error/
  Running/Idle/Unknown), never freeform.
- **Tokens** — `--text-success/-warning/-error`, `--ai-running-text`,
  `--text-tertiary`, `--surface-raised`, `--border-subtle`, `--radius-pill`.
