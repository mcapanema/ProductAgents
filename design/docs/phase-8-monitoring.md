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
- **States** — one visual per event kind (13 total), each pairing a distinct
  icon with a token-driven tone — never color alone.
- **Accessibility** — `aria-label="Session event log"` on the list; every
  row carries a real text label, not just a colored dot.
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
- **States** — `data-tier="ok"|"warning"|"critical"|"neutral"`; critical/
  warning additionally tint the card border.
- **Accessibility** — tier is a text word (`Normal`/`Elevated`/`Critical`)
  alongside color, and delta direction pairs a trend icon with the %.
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
- **States** — tier computed from percentage: ok (<70%), warning (70–90%),
  critical (>90%); each tier recolors the fill and the percentage text.
- **Accessibility** — `role="progressbar"` with `aria-valuenow/-min/-max`;
  the tier word is always printed as text, never color-only.
- **Tokens** — `--gauge-height`, `--gauge-radius`, `--gauge-track`,
  `--success`/`--signal`/`--danger`, `--text-warning`/`--text-error`.

## Execution Statistics

- **Purpose** — aggregate counts for one session: total events, distinct
  nodes touched, average inter-event latency, debate turns.
- **When to use / not** — a session summary header. Computed entirely from
  the same Event Store rows the Event Timeline renders — not a separate data
  source.
- **Anatomy** — a `p8-grid` of Metric Cards (reuses that component directly).
- **States** — latency tier flips to `warning` above a 20s average.
- **Tokens** — see Metrics Card.

## Cost Dashboard

- **Purpose** — per-node $ breakdown for one session plus a running total.
- **When to use / not** — forward-looking: no cost schema exists anywhere in
  the platform today. Keyed off the same node identifiers
  (`customer_research`, `market`, `debate`, ...) the real event vocabulary
  already uses, so a future cost source can populate it without a reshape.
- **Anatomy** — `p8-cost` → total (icon + $ figure), `p8-cost__list` of rows
  (node name, proportional bar, $ amount).
- **Accessibility** — every bar has an adjacent numeric $ label; the bar
  alone never carries the value.
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
- **Accessibility** — `role="img"` with an `aria-label` summary sentence on
  the SVG (so a screen reader gets the trend without parsing the chart);
  every point is keyboard-focusable; the table disclosure is the WCAG
  text-alternative for the data itself, not just a caption.
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
- **States** — `healthy`/`degraded`/`error`/`running`/`idle`/`unknown`, six
  total (three more than Phase 6's connector-scoped set).
- **Accessibility** — state is never color-only: dot + icon + text word all
  carry it independently.
- **Tokens** — `--text-success/-warning/-error`, `--ai-running-text`,
  `--text-tertiary`, `--surface-raised`, `--border-subtle`, `--radius-pill`.
