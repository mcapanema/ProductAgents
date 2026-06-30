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

---

## Execution Card

- **Purpose** — summary card for one run: a status colour-bar on the left
  edge, initiative title, workflow name, start time, duration, and a
  confidence bar once available.
- **Anatomy** — `p4b-exec-card` → `p4b-exec-card__bar` (status-colour edge) +
  body (head: title/workflow + `StatusBadge`; foot: started-at, duration,
  `ConfidenceBar`).
- **Variants** — `p4b-exec-card--{running|done|degraded|failed}` drive the
  edge-bar colour.
- **States** — status is reinforced by colour (edge bar) + the badge's own
  glyph and label, never colour alone.
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
- **States** — `p4b-tl-row--live` for the running stage (pulsing marker);
  `p4b-tl-row--human` for the awaiting-human stage; rows with a `detail`
  string are expand/collapse via `aria-expanded`.
- **Keyboard** — each row is `tabIndex={0}`; `ArrowDown`/`ArrowUp` move focus
  row to row, `Enter`/`Space` toggles the detail of the focused row (only
  when it has detail).
- **Accessibility** — the timeline carries `aria-label="Execution timeline"`;
  expandable rows expose `aria-expanded`; the approval actions stop click
  propagation so they don't also toggle the row.
- **Tokens** — `--p4b-tl-fill`/`--p4b-tl-text` (per-stage status colour),
  `--p4b-analyst-color` (per-analyst, e.g. `--ai-analyst-customer`),
  `--ai-running`, `--border-subtle`.

## Debate Turn Card

- **Purpose** — one debate round as a two-column split: Advocate's case for
  vs. Skeptic's case against.
- **Anatomy** — `p4b-debate-card` → `p4b-debate-card__round` label + a
  two-column `p4b-debate-card__sides` of `p4b-debate-card__side--advocate`
  / `--skeptic`, each with an icon + role label + argument paragraph.
- **Accessibility** — each voice is distinguished by icon + label, not colour
  alone (teal "scale" icon for Advocate, amber "warning" icon for Skeptic).
- **Tokens** — analyst-debate colour pairing on `--ai-*` tokens consumed via
  the side modifier classes; `--text-body-s`.

## Recommendation Card

- **Purpose** — the strategist's synthesized output: recommendation text,
  confidence bar, rationale paragraph, and expected outcomes as a checkmark
  list.
- **Anatomy** — `p4b-rec-card` → head (sparkle icon + "Recommendation" label +
  `ConfidenceBar`) + recommendation text + rationale paragraph +
  `p4b-rec-card__outcomes` (`role="list"` of checkmark items).
- **Tokens** — `ConfidenceBar`'s `--p4b-conf-fill` (one of
  `--ai-confidence-low/-medium/-high`), `--card-bg/-border/-radius`.

## Judgment Card

- **Purpose** — the Judge node's output: two calibrated score bars (evidence
  grounding, rationale coherence), a verdict badge, and an optional critique
  shown on a retry.
- **Anatomy** — `p4b-judgment-card` → head (scale icon + label + verdict
  badge) + `p4b-judgment-card__scores` of `MiniScoreBar` rows (label, track/
  fill, numeric value) + optional critique paragraph.
- **Variants** — `p4b-judgment-card--{pass|fail|retry}`.
- **Tokens** — `--p4b-judge-fill` (per score, from `--ai-confidence-low/
  -medium/-high`), `--card-bg/-border`.

## Approval Request Card

- **Purpose** — the human-in-the-loop interrupt UI shown when a run pauses at
  Governance: the recommendation, its confidence, and the three resolving
  actions.
- **Anatomy** — `p4b-approval-card` (`role="region"`, labeled "Human approval
  required") → head (diamond icon + label + `ConfidenceBar`) + recommendation
  text + `p4b-approval-card__actions` (Approve / Reject / Request analysis
  buttons).
- **Accessibility** — `role="region"` with an explicit `aria-label` so screen
  readers can jump straight to the pending decision.
- **Tokens** — `--ai-awaiting-human`, `--p4b-btn--primary/-danger/-secondary`
  button variants.

## Execution Progress

- **Purpose** — overall run progress as a single bar: stage count, current
  stage name, elapsed time.
- **Anatomy** — `p4b-exec-progress` → meta row (stages, current stage,
  elapsed) + `p4b-exec-progress__bar` (`role="progressbar"`) with a fill.
- **Accessibility** — semantic `role="progressbar"` with `aria-valuenow/
  -valuemin/-valuemax` and a descriptive `aria-label`.
- **Tokens** — `--p4b-prog-pct`, `--ai-done` (fill colour).

## Parallel Task Viewer

- **Purpose** — a compact grid showing the five analysts as mini-agent cells
  while they run concurrently.
- **Anatomy** — `p4b-parallel-viewer` → label + `p4b-parallel-viewer__grid`
  of `p4b-mini-agent` cells (dot, name, `StatusBadge`).
- **States** — `p4b-mini-agent--live` for any cell currently running.
- **Tokens** — `--p4b-mini-color` (per-analyst), `--p4b-mini-fill`
  (per-status).

## Retry Card

- **Purpose** — shown when the Judge triggers a strategist revision: attempt
  count, the critique the strategist must address, and a live "revising"
  status line.
- **Anatomy** — `p4b-retry-card` → head (refresh icon + label + attempt
  count) + critique paragraph + status row (pulsing dot + "Strategist
  revising...").
- **Tokens** — `--ai-degraded`/`--ai-running`-family colours via the shared
  status system.

## Cancellation Banner

- **Purpose** — alert banner shown when a run is cancelled mid-flight,
  reporting how many stages completed before cancellation.
- **Anatomy** — `p4b-cancel-banner` (`role="alert"`) → icon + message text +
  a dismiss button.
- **States** — dismissible (`useState` toggles it to unmounted).
- **Keyboard** — the dismiss control is a real `button` with an
  `aria-label="Dismiss cancellation notice"`.
- **Accessibility** — `role="alert"` for assertive announcement.
- **Tokens** — `--ai-failed`/`--ai-cancelled`-family colours via the `ban`
  icon and banner styling.

## Resume Panel Card

- **Purpose** — shown in a runs list when a pipeline is paused at a
  human-approval interrupt; names the stage it paused at and offers a
  resume action.
- **Anatomy** — `p4b-resume-card` → diamond icon + text ("Run paused at
  **{stage}**...") + a primary "Resume and approve" button.
- **Accessibility** — the pulsing diamond icon echoes the awaiting-human
  state used elsewhere (Status Badge, Approval Request Card) for consistency.
- **Tokens** — `--ai-awaiting-human`.

## Live Log Viewer

- **Purpose** — scrollable structured event log: timestamp, level badge, and
  message per row.
- **Anatomy** — `p4b-log-viewer` → header (title + entry count) +
  `p4b-log-viewer__body` (`role="log"`, `aria-live="polite"`) of
  `p4b-log-row` rows (ts, level, msg), coloured by level.
- **Variants** — six levels: trace, debug, info, warn, error, critical.
- **Accessibility** — `role="log"` + `aria-live="polite"` so new entries are
  announced without interrupting; level is shown as text, not colour alone.
- **Tokens** — `--ai-log-info/-debug/-trace/-warn/-error/-critical`,
  `--ai-failed` (critical row background tint).

## Streaming Console

- **Purpose** — a terminal-style panel mirroring CLI output: timestamped
  lines coloured by kind, with a blinking cursor at the active position.
- **Anatomy** — `p4b-console` → header + `p4b-console__body`
  (`role="log"`, `aria-live="polite"`) of `p4b-console__line` rows (`[ts]` +
  message) plus a trailing cursor line.
- **Variants** — line kinds: default, info, warn, error, done.
- **Accessibility** — `role="log"` + `aria-live="polite"`; monospace (Plex
  Mono) regardless of theme for terminal fidelity.
- **Tokens** — `--ai-log-info/-warn/-error`, `--font-mono`/terminal text
  styling, `--surface-sunken` (dark background regardless of theme).

## Tool Execution Card

- **Purpose** — compact card for one connector/tool call: tool name, status
  badge, argument preview, and result summary on completion.
- **Anatomy** — `p4b-tool-card` → `p4b-tool-card__border` (status edge) +
  body (head: plug icon + name + `StatusBadge`; args paragraph; optional
  result summary).
- **Tokens** — `--p4b-tool-fill` (per-status).

## Tool Call Inspector

- **Purpose** — deep-inspect a single tool call: collapsed shows tool name +
  duration; expanded shows full arguments JSON and response preview.
- **Anatomy** — native `<details>`/`<summary>` (`p4b-tool-inspector`) — zero-JS
  disclosure — with a chevron, tool name, duration meta, and two `<pre>` code
  blocks (args, response).
- **When to use / not** — debugging/audit views of a connector call. Not for
  the at-a-glance status — use Tool Execution Card for that.
- **Keyboard** — native `<details>` keyboard behaviour (`Enter`/`Space` on
  the `<summary>` toggles).
- **Accessibility** — native disclosure semantics come from `<details>` for
  free; no custom ARIA needed.
- **Tokens** — `--text-terminal` (monospace code blocks).

---

No new tokens are declared by `phase4b-execution.css` — it has no `:root`
block. All status/state colour comes from the existing `--ai-*` semantic
tokens; the `--p4b-*` custom properties referenced above are per-instance
values set inline via `style={}` in the TSX, not entries in the token layer.
