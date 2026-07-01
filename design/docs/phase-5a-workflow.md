# Phase 5A — Workflow

Planning and orchestration primitives for the roadmap/initiative-planning
domain: status, cards, milestones, timelines, the workflow-definition graph,
cross-initiative dependencies, and the connector-sync queue. Grounded in real
`pa-core` models (`Initiative`/`Feature`/`RoadmapItem`, `InitiativeStatus`/
`FeatureStatus`/`Priority`) and platform services (`WorkflowService.
evaluate_initiative`, `ConnectorService.sync`) rather than generic
placeholders — distinct from Phase 4's live-AI-run surface, which this layer
sits above. Built only from the existing token layer (no new colors). Live
gallery: `styleguide` → Workflow & CLI → 5A.

Icons are inline SVG (`viewBox 0 0 24 24`, `stroke currentColor`,
`stroke-width 1.75`, round caps), defined locally in `Phase5Workflow.tsx`.

React API: not yet productized — each component here is a
`design/styleguide/src/phase5/` demo; a stable public API is defined when it
migrates to `desktop/src/ui/`.

---

## Task Status

- **Purpose** — color+glyph+label badge for `InitiativeStatus`/`FeatureStatus`
  (proposed/idea, planned, in_progress, shipped, cancelled/deprecated) and a
  separate `Priority` badge (low/medium/high/critical).
- **When to use / not** — any place an Initiative, Feature, or RoadmapItem's
  lifecycle state or priority needs a compact label. Not for generic AI-run
  status — use Phase 4's `StatusBadge`/`--ai-*` states for that.
- **Anatomy** — `p5a-status-badge` (icon + label pill); `p5a-priority-badge`
  (flag icon + label, no pill background).
- **Variants** — `TaskStatusBadge` takes a `kind` prop: `"initiative"` (uses
  `INITIATIVE_STATUS_CFG`: proposed/planned/in_progress/shipped/cancelled) or
  `"feature"` (`FEATURE_STATUS_CFG`: idea/planned/in_progress/shipped/
  deprecated) — same anatomy, different label/icon set.
- **Sizes** — single size; compact density shrinks the status badge's height
  and padding via `[data-density="compact"]`. The priority badge has no
  compact-density override — it's unaffected.
- **States** — one of 5 status values per kind; one of 4 priority values.
- **Keyboard** — none; both badges are static, non-interactive `span`s.
- **Accessibility** — color is never the only channel: every status pairs an
  icon with its text label.
- **Content guidelines** — labels are the fixed sets in `INITIATIVE_STATUS_CFG`
  / `FEATURE_STATUS_CFG` ("Proposed"/"Idea", "Planned", "In progress",
  "Shipped"/"Deprecated", "Cancelled") and `PRIORITY_CFG` ("Low", "Medium",
  "High", "Critical") — not free text.
- **Implementation notes** — badge background is a 15% tint of the status
  color via `color-mix(in oklch, var(--p5a-badge-color) 15%, transparent)`,
  not a flat fill.
- **Tokens** — `--success`/`--text-success`, `--info`/`--text-info`,
  `--accent`/`--accent-text`, `--danger`, `--warning`, `--text-tertiary`,
  `--text-disabled`, `--radius-pill`, `--fw-semibold`.

## Stage Header

- **Purpose** — reusable header for a named group/stage: title, optional
  count, optional status badge, optional text action.
- **When to use / not** — section headers above a list/grid of cards (e.g.
  "In progress — 4"). Not a page-level heading.
- **Anatomy** — `p5a-stage-header` → title row (`p5a-stage-header__title` +
  `__count`) and meta row (status badge + `p5a-stage-header__action` button).
- **Variants** — with or without the action button.
- **Sizes** — single size; no compact-density override defined for this
  component.
- **States** — none beyond the action button's focus ring (see Keyboard);
  the header itself is static.
- **Keyboard** — the action is a real `button`, focusable with a visible ring.
- **Accessibility** — the title always renders as a semantic `<h4>`
  regardless of context — callers are responsible for keeping page heading
  levels correctly nested when reusing this component.
- **Content guidelines** — count is optional and only rendered when a number
  is passed (no "0" badge otherwise); action text is a short verb phrase
  (e.g. "View all").
- **Tokens** — `--text-heading-4`, `--text-caption`, `--accent-text`,
  `--border-subtle`, `--focus-ring-width/-offset`, `--border-focus`.

## Task Card

- **Purpose** — summary card for an Initiative or Feature: title, status,
  description, priority, owner, target quarter.
- **When to use / not** — grid/list views of initiatives. Not for the
  workflow-definition graph nodes (those use `WorkflowGraph`'s compact rect
  nodes instead).
- **Anatomy** — `p5a-task-card` → head (title + `TaskStatusBadge`),
  description paragraph, foot (`PriorityBadge` + owner + quarter).
- **Variants** — none; a single card layout — status always uses the
  `"initiative"` kind of Task Status (see above), never `"feature"`.
- **Sizes** — single size; compact density tightens the internal gap via
  `[data-density="compact"]`.
- **States** — none; a static, non-interactive summary card.
- **Keyboard** — none; not focusable.
- **Accessibility** — the card is a semantic `<article>` with `<header>`/
  `<footer>` for the head/foot regions, giving screen-reader users landmark
  structure without extra ARIA.
- **Content guidelines** — description has no line-clamp/truncation — long
  text grows the card vertically rather than being cut off; owner and
  quarter render as short strings (e.g. "R. Castellan", "Q3 2026") with
  tabular-nums for column alignment.
- **Tokens** — `--card-pad/-bg/-border/-radius`, `--text-body-m/-s`,
  `--text-caption`, `--fw-semibold`.

## Milestone

- **Purpose** — single roadmap checkpoint marker: label, date, and state
  (reached / upcoming / at-risk).
- **When to use / not** — a flat checkpoint list (vs. `ProgressTimeline`,
  which groups items by quarter).
- **Anatomy** — `p5a-milestone` row: state-colored marker icon + label + date.
- **Variants** — none; the same row layout across all three states (see
  States).
- **Sizes** — single size; no compact-density override defined.
- **States** — `reached` (success check), `upcoming` (neutral flag),
  `at-risk` (danger alert, with a danger-tinted card border).
- **Keyboard** — none; each row is a static, non-focusable `<li>`.
- **Accessibility** — state is communicated via icon + label text, not color
  alone; `at-risk` additionally gets a danger-tinted card border as a third
  channel.
- **Content guidelines** — date renders as a short human string (e.g.
  "Apr 14"), not an ISO timestamp; label is a short checkpoint name, not a
  full sentence.
- **Tokens** — `--success`, `--danger`, `--text-tertiary`, `--surface-raised`,
  `--border-subtle`, `--card-radius`.

## Progress Timeline

- **Purpose** — vertical stepper grouping roadmap items by quarter, marking
  done/current/future quarters.
- **When to use / not** — a quarter-by-quarter roadmap overview. Not a
  live-execution timeline — see Phase 4B's `ExecutionTimeline` for that.
- **Anatomy** — `p5a-progress-timeline` (rail) → `__step` per quarter, each
  with a `__dot` marker and a nested `__items` list.
- **Variants** — none; a single vertical stepper layout.
- **Sizes** — single size; no compact-density override defined.
- **States** — `data-state="done" | "current" | "future"` recolors the dot
  (`--success`, `--accent`, neutral).
- **Keyboard** — none; a static, non-interactive ordered list.
- **Accessibility** — done/current/future is color-only on the dot — no icon
  or text label distinguishes them, and there's no `aria-current`. Relies on
  list order and the quarter label for context; screen readers get no
  explicit per-quarter state announcement.
- **Content guidelines** — items per quarter are short strings (e.g.
  "Connector framework") in a plain list — no extra formatting.
- **Tokens** — `--border-subtle`, `--border-default`, `--success`, `--accent`,
  `--text-primary`, `--text-tertiary`.

## Pipeline View

- **Purpose** — bird's-eye horizontal chip row naming a workflow's stages in
  order, separated by chevrons.
- **When to use / not** — a compact, space-constrained alternative to the full
  `WorkflowGraph` (e.g. inline in a card header).
- **Anatomy** — `p5a-pipeline-view` (flex-wrap row) of `__chip` spans, each
  followed by a chevron-right icon except the last.
- **Variants** — none; a single chip-row layout.
- **Sizes** — single size; no compact-density override defined.
- **States** — none; a static list of stage names, unlike Execution Queue's
  per-item status coloring.
- **Keyboard** — none; chips are plain spans, not focusable.
- **Accessibility** — `role="list"`/`role="listitem"` on the container/chips.
- **Content guidelines** — stage names are short nouns/phrases (e.g.
  "Analysts ×5") matching the real pipeline step names, not full sentences;
  the chevron separator is decorative and omitted after the last chip.
- **Tokens** — `--surface-raised`, `--border-subtle`, `--radius-pill`,
  `--text-caption`, `--text-secondary`.

## Workflow Graph / Node / Edge

- **Purpose** — structural SVG view of a workflow *definition* (e.g. the
  `evaluate_initiative` registry entry in `WorkflowService`) — nodes and
  directed edges, not a live run's progress.
- **When to use / not** — explaining how a workflow is wired. For a *running*
  decision's live node states, use Phase 4A's `DependencyGraph`
  (`p4a-dep-graph`) instead — that one paints `--ai-*` run-state colors.
- **Anatomy** — `p5a-wf-graph` SVG → `p5a-wf-edge` lines with an arrow marker,
  `p5a-wf-node__rect` boxes with `p5a-wf-node__label` text.
- **Variants** — none; a single SVG diagram driven by the `WF_NODES`/
  `WF_EDGES` data.
- **Sizes** — the SVG scales fluidly (`width: 100%; height: auto` on a fixed
  `viewBox`) rather than exposing a discrete size variant.
- **States** — none; a static structural diagram — no live run-state coloring
  (contrast Phase 4A's `DependencyGraph`, which paints `--ai-*` run states).
- **Keyboard** — none; not focusable.
- **Accessibility** — the `<svg>` has `role="img"` + a diagram-level
  `aria-label`; each node `<g>` also has its own `role="img"`/`aria-label`,
  while the node's `<text>` label is `aria-hidden` to avoid double
  announcement.
- **Content guidelines** — node labels are short strings (e.g.
  "Analysts (×5)") sized to fit the fixed 52×32 rect — no wrapping or
  truncation, so labels must stay short.
- **Implementation notes** — the `prefers-reduced-motion` rule resets
  `stroke-dasharray` on `.p5a-wf-edge`, but no dasharray is set in the base
  rule — currently a no-op.
- **Tokens** — `--ai-edge`, `--ai-node-border`, `--surface-sunken/-raised`,
  `--border-subtle`, `--card-radius`.

## Dependency Graph

- **Purpose** — cross-initiative dependency list: which initiatives block
  which others.
- **When to use / not** — portfolio-level planning views. Distinct from Phase
  4A's dependency graph, which visualizes a single run's analyst→debate→
  strategist node graph, not relationships between separate initiatives.
- **Anatomy** — `p5a-dep-graph` list → `__row` per initiative, with an
  optional `__deps` chip naming its blockers (warning-tinted link icon).
- **Variants** — none; the `__deps` chip's presence is purely data-driven
  (whether `DEP_LINKS` names a blocker for that initiative), not a prop.
- **Sizes** — single size; no compact-density override defined.
- **States** — none; a static, non-interactive list.
- **Keyboard** — none; rows are plain `<li>`s, not focusable.
- **Accessibility** — the list has `aria-label="initiative dependencies"`;
  the "blocked by" chip pairs a link icon with text naming the blocker(s) —
  not color alone, even though the icon itself is warning-tinted.
- **Content guidelines** — blockers are joined with commas ("blocked by X,
  Y") using the same initiative names as `DEP_INITIATIVES` — no separate
  abbreviated form.
- **Tokens** — `--surface-raised`, `--border-subtle`, `--warning`,
  `--text-primary`, `--text-tertiary`.

## Execution Queue

- **Purpose** — ordered queue of connector-sync jobs (queued / syncing / done
  / error), each showing the connector, sync cursor, and time.
- **When to use / not** — the `ConnectorService.sync()` job queue. Not an
  AI-run task queue — see Phase 4A's `EvaluationQueue` (priority-ranked
  initiatives waiting to be evaluated) for that.
- **Anatomy** — `p5a-queue` → `__head` label, `__list` of `__item` rows (rank,
  status icon, connector name, cursor, elapsed/timestamp).
- **Variants** — none; a single list layout with a fixed head label
  ("Connector sync queue").
- **Sizes** — single size; compact density reduces each row's vertical
  padding via `[data-density="compact"]`.
- **States** — `queued`, `syncing`, `done`, `error` — each recolors the row's
  icon/text via `--p5a-queue-color`; the `syncing` icon is the static refresh
  glyph (not an animated spinner in this CSS).
- **Keyboard** — none; rows are static, not focusable.
- **Accessibility** — state is communicated via icon shape (clock/refresh/
  check-circle/x-circle) plus the row tint together, not color alone.
- **Content guidelines** — cursor shows an em-dash "—" when there's nothing
  to report yet (`queued`); time alternates between a relative string
  ("waiting", "running 12s") and an absolute timestamp once `done`/`error` —
  not one consistent format.
- **Tokens** — `--surface-raised/-sunken`, `--border-subtle`, `--accent`,
  `--success`, `--danger`, `--text-tertiary`, `--card-radius`.
