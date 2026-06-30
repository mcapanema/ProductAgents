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
- **States** — one of 5 status values per kind; one of 4 priority values.
- **Accessibility** — color is never the only channel: every status pairs an
  icon with its text label.
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
- **Keyboard** — the action is a real `button`, focusable with a visible ring.
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
- **Tokens** — `--card-pad/-bg/-border/-radius`, `--text-body-m/-s`,
  `--text-caption`, `--fw-semibold`.

## Milestone

- **Purpose** — single roadmap checkpoint marker: label, date, and state
  (reached / upcoming / at-risk).
- **When to use / not** — a flat checkpoint list (vs. `ProgressTimeline`,
  which groups items by quarter).
- **Anatomy** — `p5a-milestone` row: state-colored marker icon + label + date.
- **States** — `reached` (success check), `upcoming` (neutral flag),
  `at-risk` (danger alert, with a danger-tinted card border).
- **Tokens** — `--success`, `--danger`, `--text-tertiary`, `--surface-raised`,
  `--border-subtle`, `--card-radius`.

## Progress Timeline

- **Purpose** — vertical stepper grouping roadmap items by quarter, marking
  done/current/future quarters.
- **When to use / not** — a quarter-by-quarter roadmap overview. Not a
  live-execution timeline — see Phase 4B's `ExecutionTimeline` for that.
- **Anatomy** — `p5a-progress-timeline` (rail) → `__step` per quarter, each
  with a `__dot` marker and a nested `__items` list.
- **States** — `data-state="done" | "current" | "future"` recolors the dot
  (`--success`, `--accent`, neutral).
- **Tokens** — `--border-subtle`, `--border-default`, `--success`, `--accent`,
  `--text-primary`, `--text-tertiary`.

## Pipeline View

- **Purpose** — bird's-eye horizontal chip row naming a workflow's stages in
  order, separated by chevrons.
- **When to use / not** — a compact, space-constrained alternative to the full
  `WorkflowGraph` (e.g. inline in a card header).
- **Anatomy** — `p5a-pipeline-view` (flex-wrap row) of `__chip` spans, each
  followed by a chevron-right icon except the last.
- **Accessibility** — `role="list"`/`role="listitem"` on the container/chips.
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
- **States** — `queued`, `syncing` (animated refresh icon color),  `done`,
  `error` — colored via `--p5a-queue-color`.
- **Tokens** — `--surface-raised/-sunken`, `--border-subtle`, `--accent`,
  `--success`, `--danger`, `--text-tertiary`, `--card-radius`.
