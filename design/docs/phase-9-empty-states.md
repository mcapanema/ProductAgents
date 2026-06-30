# Phase 9 — Empty & transitional states

First-Run Experience, Empty Collection State (workspace/agents/projects/executions/no-results),
Initial Loading, Offline Mode, and Maintenance State — `src/phase9/Phase9EmptyStates.tsx` +
`phase9-empty-states.css`, prefixed `p9-`. Live gallery: `styleguide` → `Empty States`.

**Illustration stance: no illustrations — empty states are structural.** ProductAgents is a
telemetry "Instrument"; spot illustrations are the wrong register for it. Every state here is
built from an icon glyph in a circular badge, a title, body copy, and a primary action — the
same `fbk-state`-style shell Phase 3E established for status cards. If a future phase wants
imagery, it must be themeable (light/dark) and ship locally, per the plan's asset constraint.

**Grounding.** Empty Workspace mirrors `WorkspaceService.list`/`resolve` (Phase 6's grounding);
Empty Executions and its "like a git log of decisions" copy mirror the real session log surfaced
by `SessionService.list`/`SessionService.show` (`productagents sessions list`); Offline reuses
the exact "platform sidecar" framing from Phase 3E's offline banner, which refers to the real
`productagents ipc` NDJSON sidecar the desktop shell spawns. Empty Agents/Projects, First-Run,
No Search Results, Initial Loading, and Maintenance State have no backend contract yet —
forward-looking UX states, same posture as Phase 6's git/file-tree placeholders.

Built only from the existing token layer (no new colors — `contrast.py` still 0 failures, both
themes + CVD); reuses the `--surface-*`/`--text-*`/`--btn-*` tokens Phase 2/3 reserved and the
dashed-card pattern Phase 3E's `.fbk-state` established. Icons are inline SVG (Phosphor-style,
`stroke="currentColor"`), defined locally in `Phase9EmptyStates.tsx`.

---

## Empty Collection State

**Purpose:** a single parameterized card for any list that can be empty — workspaces, agents,
projects, executions, or a filtered/search view with nothing matching.

**When to use:** a collection view's first render after confirming the collection is genuinely
empty (not still loading — use Initial Loading for that). **When not to use:** for a temporary
network failure (use Offline Mode) or a partial result set (show the partial list instead).

**Anatomy:** icon badge (pill, `--space-48` box) → title → body copy (capped at
`--measure-prose`) → primary action button, with an optional secondary action.

**States:** five content variants (Empty workspace/agents/projects/executions/no-results) —
same structure, different icon/copy/actions.

**Accessibility:** `role="status"` (not `alert` — an empty list isn't an error); the primary
action is a real `<button>`, reachable by keyboard with a visible focus ring (`.p9-btn:focus-visible`).

**Tokens:** `--surface-sunken`, `--surface-raised`, `--border-subtle`, `--border-width-default`,
`--card-radius`, `--radius-pill`, `--text-heading-4`, `--text-body-s`, `--text-primary`,
`--text-secondary`, `--space-48/32/24/12/8/4`, `--btn-*`.

## First-Run Experience

**Purpose:** the very first thing a brand-new workspace shows — a welcome message and a
checklist of the steps that turn an empty workspace into a usable one.

**When to use:** only on the first visit to a workspace with no connectors, no evidence, and no
decision history. Once any one of those exists, fall back to the relevant Empty Collection State
instead.

**Anatomy:** icon badge → title → body copy → ordered checklist (done/pending status glyph per
step) → single primary action (always the next unfinished step).

**States:** each checklist item is `data-done="true"|"false"`; the primary action always reflects
the next pending step (illustrated here with the first step already done).

**Accessibility:** the checklist is a real `<ol>` so screen readers announce step order and
count; done/pending is conveyed by both icon shape (check vs. circle) and color, not color alone.

**Tokens:** same shell tokens as Empty Collection State, plus `--ai-running` for the done-step
icon accent.

## Initial Loading

**Purpose:** shown while a workspace's first data fetch is in flight, so the screen is never
blank between navigation and content.

**When to use:** only for the *first* load of a view (no cached data to show yet). A refresh of
already-visible data should use an inline spinner on the existing content instead, not this
full-block state.

**Anatomy:** spinner → status label → three skeleton rows previewing the eventual layout.

**States:** a single state; the label text is the only variable (e.g. "Loading workspace…").

**Accessibility:** `role="status"` with `aria-live="polite"` on the container and `aria-label`
on the spinner itself, so assistive tech announces the label once rather than on every shimmer
frame. `prefers-reduced-motion` parks the spinner rotation and the skeleton shimmer (matching
Phase 3E's `.fbk-spinner`/`.fbk-skel` reduced-motion behavior).

**Tokens:** `--ai-running`, `--dur-slow`, `--dur-slower`, `--ease-standard`, `--surface-sunken`,
`--surface-raised`, `--radius-pill`, `--space-4/8/12`.

## Offline Mode

**Purpose:** a full blocking state for when the platform sidecar is unreachable — distinct from
Phase 3E's small offline *banner*, which assumes the rest of the page still has something to
show.

**When to use:** when a view has no usable cached data to fall back to and the sidecar
connection is down. If cached data exists, prefer Phase 3E's offline banner over a view that
still has content. **When not to use:** for a single failed request (use an inline error state).

**Anatomy:** icon badge → "Offline" title → explanation → last-synced timestamp → primary "Retry
connection" action.

**States:** a single state; `lastSynced` is the only variable.

**Accessibility:** `role="alert"` — unlike the empty states, this is an interruption worth
announcing immediately.

**Tokens:** same shell tokens as Empty Collection State, with the card rendered solid
(`border-style: solid`) rather than dashed, signaling "blocking" vs. "nothing here yet."

## Maintenance State

**Purpose:** a planned, server-driven pause, distinct from Offline's unplanned connectivity
loss.

**When to use:** when the platform announces a scheduled maintenance window. **When not to
use:** for client-side connectivity issues — that's Offline Mode.

**Anatomy:** icon badge → title → explanation → expected-return time → secondary "Status page"
action (secondary, not primary — there is nothing the user can do to resolve it themselves).

**States:** a single state; `eta` is the only variable.

**Accessibility:** `role="status"` (informational, not an error the user caused or can fix).

**Tokens:** same shell tokens as Offline Mode.
