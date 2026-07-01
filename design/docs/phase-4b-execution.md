# Phase 4B — Execution & Streaming Reasoning

The centrepiece of the AI-differentiating layer: components that make a live
decision run legible end to end — run summary cards, the full pipeline
timeline (parallel analysts → debate → strategist → judge → risk →
governance → human approval), the debate dialectic, judgment scores, retry
and cancellation states, and tool-call/log inspection. Built only from the
token layer; all AI state uses `--ai-*` tokens. Live gallery: `styleguide` →
4B · Execution.

Icons are local inline SVG (`viewBox 0 0 24 24`, `stroke currentColor`,
`stroke-width 1.75`, round caps), the same convention redeclared per-file as
in 3A and 4A.

React API: not yet productized — each component here is a
`design/styleguide/src/phase4/` demo; a stable public API is defined when it
migrates to `desktop/src/ui/`.

---

## Execution Card

- **Purpose** — summary card for one run: a status colour-bar on the left
  edge, initiative title, workflow name, start time, duration, and a
  confidence bar once available.
- **When to use / not** — a run-summary list (e.g. a dashboard or runs list).
  Not for the live in-progress detail — use Execution Timeline for that.
- **Anatomy** — `p4b-exec-card` → `p4b-exec-card__bar` (status-colour edge) +
  body (head: title/workflow + `StatusBadge`; foot: started-at, duration,
  `ConfidenceBar`).
- **Variants** — `p4b-exec-card--{running|done|degraded|failed}` drive the
  edge-bar colour.
- **Sizes** — single size; compact density reduces body padding.
- **States** — status is reinforced by colour (edge bar) + the badge's own
  glyph and label, never colour alone.
- **Keyboard** — none; a static summary card, not focusable.
- **Accessibility** — the status colour-bar is `aria-hidden`; status is
  conveyed via the `StatusBadge`'s icon + label, never the bar alone.
- **Content guidelines** — title truncates with an ellipsis on overflow;
  workflow name and meta stay to one line.
- **Implementation notes** — the `running` variant additionally pulses the
  edge bar (`p4b-pulse`), on top of the colour the variant already sets.
- **Tokens** — `--p4b-exec-fill` (per-status, from `--ai-running/-done
  /-degraded/-failed`), `--card-bg/-border/-radius/-pad`.

## Execution Timeline

- **Purpose** — the full decision pipeline in one glanceable view: a parallel
  group (the five analysts + recall running concurrently) joined into a
  sequential spine (debate → strategist → judge → risk → governance →
  approval), each row expandable for detail, with an optional final
  recommendation summary.
- **When to use / not** — the primary live-run view. This is the centrepiece
  component of Phase 4B.
- **Anatomy** — `p4b-timeline` → `p4b-tl-parallel-group` (header + rows) +
  `p4b-tl-join` connector + `p4b-tl-sequential` rows, optionally closed by
  `p4b-tl-result` (recommendation text + `ConfidenceBar`). Each row
  (`p4b-tl-row`) has a marker (icon or pulsing dot for the live stage), an
  optional analyst colour strip, name + `StatusBadge` + expand chevron, an
  expandable detail paragraph, and time/duration meta. The `awaiting-human`
  row can show inline Approve/Reject/Request-analysis actions.
- **Variants** — none as a component prop; the gallery shows three data
  states (mid-run, approval-pending, completed) built from different
  `stages` arrays, not CSS variants.
- **Sizes** — single size; compact density reduces row padding, marker size,
  parallel-group indent, and meta column width.
- **States** — `p4b-tl-row--live` for the running stage (pulsing marker);
  `p4b-tl-row--human` for the awaiting-human stage; rows with a `detail`
  string are expand/collapse via `aria-expanded`.
- **Keyboard** — each row is `tabIndex={0}`; `ArrowDown`/`ArrowUp` move focus
  row to row, `Enter`/`Space` toggles the detail of the focused row (only
  when it has detail).
- **Accessibility** — the timeline carries `aria-label="Execution timeline"`;
  expandable rows expose `aria-expanded`; the approval actions stop click
  propagation so they don't also toggle the row.
- **Content guidelines** — the expandable `detail` string is one short
  paragraph combining a confidence figure and a one-line finding; keep it
  self-contained since it renders standalone when expanded.
- **Implementation notes** — parallel vs. sequential grouping is driven by
  each stage's `parallel: true` flag, not a fixed count; arrow-key navigation
  walks a flat `rowRefs` array spanning both groups.
- **Tokens** — `--p4b-tl-fill`/`--p4b-tl-text` (per-stage status colour),
  `--p4b-analyst-color` (per-analyst, e.g. `--ai-analyst-customer`),
  `--ai-running`, `--border-subtle`.

## Debate Turn Card

- **Purpose** — one debate round as a two-column split: Advocate's case for
  vs. Skeptic's case against.
- **When to use / not** — the debate-round transcript in a run's detail view.
  Not for a single-sided argument — the two-column layout assumes both an
  advocate and a skeptic case are present.
- **Anatomy** — `p4b-debate-card` → `p4b-debate-card__round` label + a
  two-column `p4b-debate-card__sides` of `p4b-debate-card__side--advocate`
  / `--skeptic`, each with an icon + role label + argument paragraph.
- **Variants** — none; always the fixed advocate/skeptic pair.
- **Sizes** — single size; compact density reduces side padding.
- **States** — none; a static display card (no hover/selected/focus states).
- **Keyboard** — none; not interactive.
- **Accessibility** — each voice is distinguished by icon + label, not colour
  alone (teal "scale" icon for Advocate, amber "warning" icon for Skeptic).
- **Content guidelines** — advocate/skeptic arguments are full paragraphs
  (2–3 sentences); keep both sides roughly balanced in length so the
  two-column layout doesn't look lopsided.
- **Implementation notes** — the two-column layout stacks to one column
  under 600px, with the advocate side's border switching from right to
  bottom.
- **Tokens** — analyst-debate colour pairing on `--ai-*` tokens consumed via
  the side modifier classes; `--text-body-s`.

## Recommendation Card

- **Purpose** — the strategist's synthesized output: recommendation text,
  confidence bar, rationale paragraph, and expected outcomes as a checkmark
  list.
- **When to use / not** — the Strategist's finished output in a run's detail
  view. Not for a partial/streaming recommendation — pair with Streaming
  Text (4C) while the text is still generating.
- **Anatomy** — `p4b-rec-card` → head (sparkle icon + "Recommendation" label +
  `ConfidenceBar`) + recommendation text + rationale paragraph +
  `p4b-rec-card__outcomes` (`role="list"` of checkmark items).
- **Variants** — none.
- **Sizes** — single size; compact density tightens gaps and padding.
- **States** — none; a static display card.
- **Keyboard** — none; not interactive.
- **Accessibility** — the expected-outcomes list uses `role="list"` with a
  check icon per item; the icon is decorative, the text carries the meaning.
- **Content guidelines** — expected outcomes are short, one-line, and
  quantified where possible (e.g. "Retention improves by 8–12%…").
- **Tokens** — `ConfidenceBar`'s `--p4b-conf-fill` (one of
  `--ai-confidence-low/-medium/-high`), `--card-bg/-border/-radius`.

## Judgment Card

- **Purpose** — the Judge node's output: two calibrated score bars (evidence
  grounding, rationale coherence), a verdict badge, and an optional critique
  shown on a retry.
- **When to use / not** — the Judge node's evaluation output in a run's
  detail view. Not for the Strategist's own recommendation — use
  Recommendation Card for that.
- **Anatomy** — `p4b-judgment-card` → head (scale icon + label + verdict
  badge) + `p4b-judgment-card__scores` of `MiniScoreBar` rows (label, track/
  fill, numeric value) + optional critique paragraph.
- **Variants** — `p4b-judgment-card--{pass|fail|retry}`.
- **Sizes** — single size, capped at a 400px max width
  (`width: min(100%, 400px)`); compact density tightens gaps and shrinks the
  score-label column.
- **States** — none beyond the pass/fail/retry variant (see Variants); no
  hover or interactive state.
- **Keyboard** — none; not interactive.
- **Accessibility** — the verdict pill shows the verdict as uppercase text,
  not colour alone; each score bar pairs a numeric value with its fill,
  matching the Confidence Bar pattern.
- **Content guidelines** — the two score labels ("Evidence grounding",
  "Rationale coherence") match the Judge node's actual rubric dimensions;
  critique is optional freeform text shown only on retry/fail.
- **Tokens** — `--p4b-judge-fill` (per score, from `--ai-confidence-low/
  -medium/-high`), `--card-bg/-border`.

## Approval Request Card

- **Purpose** — the human-in-the-loop interrupt UI shown when a run pauses at
  Governance: the recommendation, its confidence, and the three resolving
  actions.
- **When to use / not** — the human-in-the-loop interrupt when a run pauses
  at Governance. Not for a routine, non-blocking confirmation — this is
  reserved for the pipeline's one HITL gate.
- **Anatomy** — `p4b-approval-card` (`role="region"`, labeled "Human approval
  required") → head (diamond icon + label + `ConfidenceBar`) + recommendation
  text + `p4b-approval-card__actions` (Approve / Reject / Request analysis
  buttons).
- **Variants** — none.
- **Sizes** — single size; compact density tightens gaps and padding.
- **States** — a single always-on attention state: a pulsing indigo border
  (`p4b-border-glow`) while a decision is pending; the card is only rendered
  while awaiting a response, so there's no separate resting state.
- **Keyboard** — the three action buttons are native `<button>` elements,
  standard Tab/Enter/Space operable.
- **Accessibility** — `role="region"` with an explicit `aria-label` so screen
  readers can jump straight to the pending decision.
- **Content guidelines** — recommendation text mirrors the Strategist's
  output (see Recommendation Card) verbatim; this is the pending
  recommendation itself, not a summary of it.
- **Implementation notes** — shares the `p4b-border-glow` pulse animation
  with the Execution Timeline's awaiting-human row and Resume Panel Card,
  keeping the HITL visual language consistent across all three.
- **Tokens** — `--ai-awaiting-human`, `--p4b-btn--primary/-danger/-secondary`
  button variants.

## Execution Progress

- **Purpose** — overall run progress as a single bar: stage count, current
  stage name, elapsed time.
- **When to use / not** — an at-a-glance overall run-progress readout (e.g. a
  header or summary bar). Not for stage-by-stage detail — use Execution
  Timeline for that.
- **Anatomy** — `p4b-exec-progress` → meta row (stages, current stage,
  elapsed) + `p4b-exec-progress__bar` (`role="progressbar"`) with a fill.
- **Variants** — none.
- **Sizes** — single size; compact density reduces the bar height (6px →
  4px).
- **States** — none; a continuous fill from 0–100%, no discrete state
  variants.
- **Keyboard** — none; not focusable.
- **Accessibility** — semantic `role="progressbar"` with `aria-valuenow/
  -valuemin/-valuemax` and a descriptive `aria-label`.
- **Content guidelines** — `currentStage` is a short stage/node name;
  `elapsed` is a short duration string (e.g. "2 m 01 s").
- **Tokens** — `--p4b-prog-pct`, `--ai-done` (fill colour).

## Parallel Task Viewer

- **Purpose** — a compact grid showing the five analysts as mini-agent cells
  while they run concurrently.
- **When to use / not** — a compact, glanceable widget for the five analysts
  running concurrently (e.g. a header). Not for a detailed per-analyst
  view — use Timeline or Agent Card for that.
- **Anatomy** — `p4b-parallel-viewer` → label + `p4b-parallel-viewer__grid`
  of `p4b-mini-agent` cells (dot, name, `StatusBadge`).
- **Variants** — none.
- **Sizes** — single size; compact density reduces cell padding.
- **States** — `p4b-mini-agent--live` for any cell currently running.
- **Keyboard** — none; a static grid, cells aren't focusable or clickable.
- **Accessibility** — each cell's dot is decorative colour-only; the
  embedded `StatusBadge` (icon + text label) carries the actual status.
- **Content guidelines** — names are the five fixed analyst names (Customer,
  Analytics, Market, Business, Technical), not free text.
- **Implementation notes** — the grid's border logic (`:nth-child(5n)`,
  `:nth-last-child(-n+5)`) assumes exactly 5 cells; adding a 6th analyst
  needs the CSS updated to match, not just new data.
- **Tokens** — `--p4b-mini-color` (per-analyst), `--p4b-mini-fill`
  (per-status).

## Retry Card

- **Purpose** — shown when the Judge triggers a strategist revision: attempt
  count, the critique the strategist must address, and a live "revising"
  status line.
- **When to use / not** — shown live when the Judge triggers a Strategist
  revision, mid-run. Not for the Judge's own score output — use Judgment
  Card for that.
- **Anatomy** — `p4b-retry-card` → head (refresh icon + label + attempt
  count) + critique paragraph + status row (pulsing dot + "Strategist
  revising...").
- **Variants** — none.
- **Sizes** — single size; compact density tightens gaps.
- **States** — a single always-on live state (pulsing status dot +
  "Strategist revising…" text) while the retry is in flight; no separate
  resting/idle variant.
- **Keyboard** — none; not interactive.
- **Accessibility** — the pulsing status dot is `aria-hidden`; the adjacent
  "Strategist revising…" text carries the meaning.
- **Content guidelines** — critique text is the Judge's verbatim critique
  (see Judgment Card); attempt count mirrors the configured retry budget.
- **Tokens** — `--ai-degraded`/`--ai-running`-family colours via the shared
  status system.

## Cancellation Banner

- **Purpose** — alert banner shown when a run is cancelled mid-flight,
  reporting how many stages completed before cancellation.
- **When to use / not** — an alert when a run is cancelled mid-flight. Not
  for a run that failed on its own — use the failed `ExecutionCard`/
  `StatusBadge` state; cancellation implies a user- or system-initiated stop.
- **Anatomy** — `p4b-cancel-banner` (`role="alert"`) → icon + message text +
  a dismiss button.
- **Variants** — none.
- **Sizes** — single size; compact density reduces padding.
- **States** — dismissible (`useState` toggles it to unmounted).
- **Keyboard** — the dismiss control is a real `button` with an
  `aria-label="Dismiss cancellation notice"`.
- **Accessibility** — `role="alert"` for assertive announcement.
- **Content guidelines** — the message is a fixed template naming completed
  vs. total stage count; don't add extra detail here — use a Live Log Viewer
  entry for that.
- **Implementation notes** — dismissal is local component state (`useState`)
  that unmounts the banner entirely; there's no re-show or undo, so treat it
  as fire-and-forget.
- **Tokens** — `--ai-failed`/`--ai-cancelled`-family colours via the `ban`
  icon and banner styling.

## Resume Panel Card

- **Purpose** — shown in a runs list when a pipeline is paused at a
  human-approval interrupt; names the stage it paused at and offers a
  resume action.
- **When to use / not** — a runs list showing a paused-at-approval run. Not
  for the live approval UI itself — use Approval Request Card once the user
  opens that run.
- **Anatomy** — `p4b-resume-card` → diamond icon + text ("Run paused at
  **{stage}**...") + a primary "Resume and approve" button.
- **Variants** — none.
- **Sizes** — single size; compact density tightens gap and padding.
- **States** — a single always-on attention state (pulsing border + icon)
  while paused; no separate resting state.
- **Keyboard** — the "Resume and approve" button is a native `<button>`,
  standard Tab/Enter/Space operable.
- **Accessibility** — the pulsing diamond icon echoes the awaiting-human
  state used elsewhere (Status Badge, Approval Request Card) for consistency.
- **Content guidelines** — message is a fixed template naming the paused
  stage in bold; keep the stage name to the pipeline's actual node name
  (e.g. "Governance").
- **Implementation notes** — reuses the same `p4b-border-glow` pulse as
  Approval Request Card and the Timeline's awaiting-human row.
- **Tokens** — `--ai-awaiting-human`.

## Live Log Viewer

- **Purpose** — scrollable structured event log: timestamp, level badge, and
  message per row.
- **When to use / not** — structured/debug event inspection during or after
  a run. Not for user-facing narrative output — use Streaming Console for
  CLI-style output or Execution Timeline for the plain-language summary.
- **Anatomy** — `p4b-log-viewer` → header (title + entry count) +
  `p4b-log-viewer__body` (`role="log"`, `aria-live="polite"`) of
  `p4b-log-row` rows (ts, level, msg), coloured by level.
- **Variants** — six levels: trace, debug, info, warn, error, critical.
- **Sizes** — single size; the body scrolls internally at a 280px
  max-height; compact density tightens row padding.
- **States** — the `critical` level additionally tints the whole row's
  background (not just the level text), for extra weight over the other
  five levels.
- **Keyboard** — none; a scrollable read-only log, rows aren't focusable.
- **Accessibility** — `role="log"` + `aria-live="polite"` so new entries are
  announced without interrupting; level is shown as text, not colour alone.
- **Content guidelines** — messages are raw one-line log strings
  (`module: event detail`); level text is uppercased.
- **Tokens** — `--ai-log-info/-debug/-trace/-warn/-error/-critical`,
  `--ai-failed` (critical row background tint).

## Streaming Console

- **Purpose** — a terminal-style panel mirroring CLI output: timestamped
  lines coloured by kind, with a blinking cursor at the active position.
- **When to use / not** — mirroring literal CLI output for a headless
  `productagents run` session. Not for structured/leveled debugging — use
  Live Log Viewer for that.
- **Anatomy** — `p4b-console` → header + `p4b-console__body`
  (`role="log"`, `aria-live="polite"`) of `p4b-console__line` rows (`[ts]` +
  message) plus a trailing cursor line.
- **Variants** — line kinds: default, info, warn, error, done.
- **Sizes** — single size; body scrolls at a 320px max-height; compact
  density tightens line padding.
- **States** — the trailing blinking cursor line is always rendered — there
  is no "done" state that removes it, unlike Streaming Text in 4C.
- **Keyboard** — none; a scrollable read-only log, not focusable.
- **Accessibility** — `role="log"` + `aria-live="polite"`; monospace (Plex
  Mono) regardless of theme for terminal fidelity.
- **Content guidelines** — timestamps are bracketed `[HH:MM:SS]`; message
  text mirrors literal CLI phrasing (e.g. "judge: retry requested (...)").
- **Implementation notes** — the dark background is a forced token
  (`--surface-sunken`), not theme-dependent, so the console stays legible
  even in light mode.
- **Tokens** — `--ai-log-info/-warn/-error`, `--font-mono`/terminal text
  styling, `--surface-sunken` (dark background regardless of theme).

## Tool Execution Card

- **Purpose** — compact card for one connector/tool call: tool name, status
  badge, argument preview, and result summary on completion.
- **When to use / not** — a compact, at-a-glance summary of one
  connector/tool call in a stream or list. Not for deep inspection of
  arguments/response — use Tool Call Inspector for that.
- **Anatomy** — `p4b-tool-card` → `p4b-tool-card__border` (status edge) +
  body (head: plug icon + name + `StatusBadge`; args paragraph; optional
  result summary).
- **Variants** — none beyond the status-driven border colour
  (`--p4b-tool-fill`), matching Execution Card's pattern.
- **Sizes** — single size; compact density reduces body padding.
- **States** — none beyond the `status` prop (see Tokens); a passive
  summary card with no hover/interactive state.
- **Keyboard** — none; not focusable.
- **Accessibility** — the status edge-bar is `aria-hidden`; status is
  carried by the embedded `StatusBadge`.
- **Content guidelines** — `args` renders as a raw JSON string (monospace,
  wraps aggressively); `resultSummary` is one short plain-language sentence,
  not JSON.
- **Tokens** — `--p4b-tool-fill` (per-status).

## Tool Call Inspector

- **Purpose** — deep-inspect a single tool call: collapsed shows tool name +
  duration; expanded shows full arguments JSON and response preview.
- **Anatomy** — native `<details>`/`<summary>` (`p4b-tool-inspector`) — zero-JS
  disclosure — with a chevron, tool name, duration meta, and two `<pre>` code
  blocks (args, response).
- **When to use / not** — debugging/audit views of a connector call. Not for
  the at-a-glance status — use Tool Execution Card for that.
- **Variants** — none.
- **Sizes** — single size; compact density reduces trigger and section
  padding.
- **States** — collapsed / expanded, driven by the native `open` attribute
  (the chevron rotates 90° via `[open]`); no other states.
- **Keyboard** — native `<details>` keyboard behaviour (`Enter`/`Space` on
  the `<summary>` toggles).
- **Accessibility** — native disclosure semantics come from `<details>` for
  free; no custom ARIA needed.
- **Content guidelines** — arguments and response are raw, pre-formatted
  text (JSON or similar) rendered verbatim in `<pre>`; no truncation or
  syntax highlighting.
- **Tokens** — `--text-terminal` (monospace code blocks).

---

No new tokens are declared by `phase4b-execution.css` — it has no `:root`
block. All status/state colour comes from the existing `--ai-*` semantic
tokens; the `--p4b-*` custom properties referenced above are per-instance
values set inline via `style={}` in the TSX, not entries in the token layer.
