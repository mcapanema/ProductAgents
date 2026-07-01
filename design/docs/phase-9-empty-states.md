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

React API: not yet productized — each component here is a `design/styleguide/src/phase9/` demo;
a stable public API is defined when it migrates to `desktop/src/ui/`.

---

## Empty Collection State

**Purpose:** a single parameterized card for any list that can be empty — workspaces, agents,
projects, executions, or a filtered/search view with nothing matching.

**When to use:** a collection view's first render after confirming the collection is genuinely
empty (not still loading — use Initial Loading for that). **When not to use:** for a temporary
network failure (use Offline Mode) or a partial result set (show the partial list instead).

**Anatomy:** icon badge (pill, `--space-48` box) → title → body copy (capped at
`--measure-prose`) → primary action button, with an optional secondary action.

**Variants:** five content configurations (Empty workspace/agents/projects/executions/no-results)
— same structure, different icon/copy/primary action; only the executions variant also renders a
secondary action ("Import scenario").

**Sizes:** single size — badge icon is always `lg` (`--icon-xl` in the `--space-48` box); no
compact-density override.

**States:** static, one render per variant — no loading/error sub-state of its own; hover/focus-visible
belong to the action button(s) (`.p9-btn:hover`/`:focus-visible`), not the card.

**Accessibility:** `role="status"` (not `alert` — an empty list isn't an error); the primary
action is a real `<button>`, reachable by keyboard with a visible focus ring (`.p9-btn:focus-visible`).

**Keyboard:** primary/secondary are real `<button>`s in natural tab order; no custom key handling.

**Content guidelines:** title is a short noun phrase naming the absence ("No workspace yet", "No
results"); body is one to two sentences stating what the collection is for and the action that
fixes it, using real platform nouns (workspace, connectors, initiatives, decision history), never
generic filler.

**Tokens:** `--surface-sunken`, `--surface-raised`, `--border-subtle`, `--border-width-default`,
`--card-radius`, `--radius-pill`, `--icon-xl`, `--text-heading-4`, `--text-body-s`, `--text-primary`,
`--text-secondary`, `--space-48/32/24/12/8/4`, `--btn-*`.

## First-Run Experience

**Purpose:** the very first thing a brand-new workspace shows — a welcome message and a
checklist of the steps that turn an empty workspace into a usable one.

**When to use:** only on the first visit to a workspace with no connectors, no evidence, and no
decision history. **When not to use:** once any one of those exists — fall back to the relevant
Empty Collection State instead.

**Anatomy:** icon badge → title → body copy → ordered checklist (done/pending status glyph per
step) → single primary action (always the next unfinished step).

**Variants:** single variant — the checklist's length and copy are caller-supplied `steps` data,
not a fixed set of presets.

**Sizes:** single size — badge icon `lg` (`--icon-xl`), checklist status glyphs `sm` (`--icon-sm`).

**States:** each checklist item is `data-done="true"|"false"`; the primary action always reflects
the next pending step (illustrated here with the first step already done).

**Accessibility:** the checklist is a real `<ol>` so screen readers announce step order and
count; done/pending is conveyed by both icon shape (check vs. circle) and color, not color alone.

**Keyboard:** only the primary action button is interactive (real `<button>`, tab order);
checklist items are plain `<li>`s, not focusable — `done` is read-only, caller-driven state in
this gallery, not something the user toggles here.

**Content guidelines:** step labels name a concrete platform action in imperative form ("Connect
a workspace", "Add an evidence source", "Run your first evaluation"), the same workspace/evidence/
decision-run vocabulary the file's Grounding section calls out.

**Implementation notes:** done/pending is driven by the `data-done` attribute on each `<li>`
(`.p9-checklist__item[data-done="true"]`), not a class toggle.

**Tokens:** same shell tokens as Empty Collection State, plus `--icon-sm` (checklist glyphs) and
`--ai-running` for the done-step icon accent.

## Initial Loading

**Purpose:** shown while a workspace's first data fetch is in flight, so the screen is never
blank between navigation and content.

**When to use:** only for the *first* load of a view (no cached data to show yet). **When not to
use:** a refresh of already-visible data — use an inline spinner on the existing content instead,
not this full-block state.

**Anatomy:** spinner → status label → three skeleton rows previewing the eventual layout.

**Variants:** none — see States (only the label text varies).

**Sizes:** single size — spinner is fixed at `--icon-xl`; skeleton rows are fixed at `--space-12`
tall.

**States:** a single state; the label text is the only variable (e.g. "Loading workspace…").

**Accessibility:** `role="status"` with `aria-live="polite"` on the container announces the label
text once rather than on every shimmer frame; the spinner SVG itself is `aria-hidden="true"`
(purely decorative — the label carries the meaning, not `aria-label` on the spinner).
`prefers-reduced-motion` parks the spinner rotation and the skeleton shimmer (matching Phase 3E's
`.fbk-spinner`/`.fbk-skel` reduced-motion behavior).

**Keyboard:** none — fully static, no focusable elements.

**Content guidelines:** label is a present-progressive phrase ending in an ellipsis ("Loading
workspace…"), naming the concrete thing loading, not a generic "Loading…".

**Implementation notes:** the card renders solid, not dashed, unlike Empty Collection State/First-Run
— the skeleton rows are `--surface-sunken`, which would be invisible against a `--surface-sunken`
dashed card, so `[data-kind="loading"]` shares the same solid-background CSS rule as
Offline/Maintenance for a different reason (contrast, not "blocking" semantics).

**Tokens:** `--ai-running`, `--dur-slow`, `--dur-slower`, `--ease-standard`, `--surface-sunken`,
`--surface-raised`, `--radius-pill`, `--icon-xl`, `--border-subtle`, `--space-4/8/12`.

## Offline Mode

**Purpose:** a full blocking state for when the platform sidecar is unreachable — distinct from
Phase 3E's small offline *banner*, which assumes the rest of the page still has something to
show.

**When to use:** when a view has no usable cached data to fall back to and the sidecar
connection is down. If cached data exists, prefer Phase 3E's offline banner over a view that
still has content. **When not to use:** for a single failed request (use an inline error state).

**Anatomy:** icon badge → "Offline" title → explanation → last-synced timestamp → primary "Retry
connection" action.

**Variants:** none — content-parameterized only (see States).

**Sizes:** single size — badge icon `lg` (`--icon-xl`); same shell dimensions as Empty Collection
State.

**States:** a single state; `lastSynced` is the only variable.

**Accessibility:** `role="alert"` — unlike the empty states, this is an interruption worth
announcing immediately.

**Keyboard:** "Retry connection" is a real `<button>`, in tab order; no custom key handling.

**Content guidelines:** the meta line follows a fixed "Last synced {relative time}" pattern; body
names the concrete cause ("Can't reach the platform sidecar") rather than a generic "You're
offline."

**Implementation notes:** the solid (not dashed) card background is a shared CSS rule
(`[data-kind="offline"], [data-kind="maintenance"], [data-kind="loading"]`), not an
offline-specific override.

**Tokens:** same shell tokens as Empty Collection State, with the card rendered solid
(`border-style: solid`) rather than dashed, signaling "blocking" vs. "nothing here yet."

## Maintenance State

**Purpose:** a planned, server-driven pause, distinct from Offline's unplanned connectivity
loss.

**When to use:** when the platform announces a scheduled maintenance window. **When not to
use:** for client-side connectivity issues — that's Offline Mode.

**Anatomy:** icon badge → title → explanation → expected-return time → secondary "Status page"
action (secondary, not primary — there is nothing the user can do to resolve it themselves).

**Variants:** none — content-parameterized only (see States).

**Sizes:** single size — badge icon `lg` (`--icon-xl`); same shell dimensions as Offline Mode.

**States:** a single state; `eta` is the only variable.

**Accessibility:** `role="status"` (informational, not an error the user caused or can fix).

**Keyboard:** "Status page" is a real `<button>`, in tab order; not wired to actual navigation in
this gallery despite the label implying an external page (no `href`/link semantics).

**Content guidelines:** the meta line follows a fixed "Expected back {eta}" pattern, the same
convention as Offline Mode's "Last synced" line; body names the concrete impact ("Decision runs
are paused") rather than a generic "Please check back later."

**Tokens:** same shell tokens as Offline Mode.
