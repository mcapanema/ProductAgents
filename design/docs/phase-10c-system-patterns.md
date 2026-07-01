# Phase 10C — System & recovery patterns

Error Recovery, Permission Requests, and Notification Strategy —
`src/phase10/Phase10CSystemPatterns.tsx` + `phase10c-system-patterns.css`, prefixed `p10c-`.
Live gallery: `styleguide` → `System Patterns`.

**This is a patterns doc, not a component spec.** Error Recovery and Permission Requests are new
interactions, so their chrome (`.p10c-*`) is local, mirroring the dialog/button/field shells
Phase 3C/3F/10A already established — the one-file-per-phase convention every prior module
follows. Notification Strategy is different on purpose: it is **only** a decision — which of four
existing notification components to reach for — so it reuses the real `.fbk-*` toast/banner/inline
classes from Phase 3E's feedback module directly (imported into this file) instead of
re-declaring them. Where a demo needs a dialog, it reuses the same tokens Phase 3F/10A's dialog
components established, re-declared locally per convention.

**Grounding.** Error recovery is drawn from `CLAUDE.md`'s core conventions: "Nodes degrade, never
crash" (`packages/pa-agents`) and the connector sync's partial-success shape — some GitHub issues
normalize into `CustomerFeedback`, some don't, per run. Permission requests are the UI shape behind
the real `human_approval` graph node and the advisory `governance` step: the recommendation's
rationale (evidence grounding + rationale coherence, scored by the `judge` node) is shown before
the human decides, never after. The notification matrix's four examples are drawn from real
ProductAgents events — a connector sync completing (toast), a run completing in a degraded state
(banner), an invalid connector token (inline), and an unsaved edit (blocking dialog).

Built only from the existing token layer (no new colors — `contrast.py` still reports 0 failures,
both themes). Icons are inline SVG (Phosphor-style, `stroke="currentColor"`), defined locally in
`Phase10CSystemPatterns.tsx`.

React API: not yet productized — each component here is a `design/styleguide/src/phase10/`
demo; a stable public API is defined when it migrates to `desktop/src/ui/`.

---

## Error Recovery

**Purpose:** show a failed operation the way the backend actually fails it — with the real cause,
a way back, and (when the operation had multiple parts) a way to retry just what didn't work.

**When to use:** any operation that can fail mid-flight and matters enough to explain — a decision
run aborted by a rate-limited provider, a connector sync where some items synced and some didn't.
**When not to use:** don't manufacture a recovery UI for operations that can't meaningfully fail
from the user's point of view (a client-side toggle) — that's the Notification Strategy pattern's
"nothing to recover from" case, not this one.

**Anatomy — single operation:** a trigger button that stays visible and disabled with a spinner
label while running (same convention as Phase 10A's Long-Running Operations) → on failure, an
inline error card with a real cause sentence (never "something went wrong") and a **Retry**
action that re-attempts the same operation. **Anatomy — partial success:** a list of the
operation's items, each showing its own outcome (succeeded / failed, with the failed ones showing
their own cause inline) → a summary line ("N of M synced, K failed") → a **Retry failed (K)**
action that re-attempts only the failed subset, never the whole batch.

**Variants:** two demoed — single operation (inline error card + Retry) and partial success
(per-item list + "Retry failed (K)"), chosen by whether the operation has sub-parts that can
independently fail.

**Sizes:** single size for both variants — error card and item list cap at `--measure-prose`.

**States:** idle → running (trigger disabled + spinner) → failed (cause + Retry shown) or
succeeded. Partial success adds a per-item state (`pending` / `ok` / `failed`) independent of the
overall run state, so a retry only re-runs the items still in `failed`.

**Accessibility:** the error card has `role="alert"` (it's new information the user didn't ask
for); the cause is real text content, not conveyed by icon or color alone. Each failed list item's
cause sits directly under its label so a screen reader announces cause-with-context, not a
detached error list.

**Keyboard:** Retry and Retry-failed are plain `<button>`s in normal tab order — nothing here is a
focus-trapped surface, so no custom key handling is needed.

**Content guidelines:** the cause sentence is real and specific ("The model provider rate-limited
the request (HTTP 429)…", "Payload missing the required `action` field…"), never a generic
"Something went wrong"; the summary line follows a fixed "N of M synced, K failed" template.

**Implementation notes:** outcomes are deterministic, not randomized (first attempt fails, every
retry succeeds) — a `ponytail:` comment in the source notes this keeps the recovery *shape*
legible rather than simulating a flaky backend.

**Tokens:** `--fb-error-{bg,border,text,icon}`, `--fb-success-icon`, `--ai-running`, `--ai-done`,
`--btn-*`, `--dur-slow` (spinner rotation, parked under `prefers-reduced-motion`).

**Do** show the operation's actual failure reason and keep a next action visible at all times.
**Don't** force a full re-run when only part of a batch failed — that repeats work that already
succeeded and erodes trust in the retry action itself.

## Permission Requests

**Purpose:** ask for approval before a consequential action happens, with enough context that the
decision can be made without leaving the dialog — the UI shape behind the real `human_approval`
graph node and the advisory `governance` step that precedes it.

**When to use:** any action gated on human judgment where the system has already done analysis
worth showing — approving a `Recommendation` the strategist/judge/risk nodes produced.
**When not to use:** for actions that don't need a second party's judgment (see Phase 10A's
Confirmation Flows decision tree for the "is this even worth a gate" question) — this pattern
assumes the answer is already "yes, and the person deciding needs context," not just "yes."

**Anatomy:** a medallion + title naming exactly what's being approved → a rationale list (the
evidence and reasoning that led here — grounded in the debate/judge output, not asserted) → a
consequence statement (what happens on Approve, what happens on Reject) shown **before** any
button is pressed → three actions: **Request more info** (least consequential, first in DOM
order), **Reject**, **Approve** (primary, rightmost). Choosing "Request more info" reveals an
inline question field in place, without closing the dialog or discarding the context already
shown.

**Variants:** none — one dialog shape; "Request more info" reveals an inline panel in place
rather than branching to a different dialog variant.

**Sizes:** single size — `--width-dialog-sm`, same shell as Phase 10A's Confirmation Flows and
Destructive Actions; medallion at `--size-avatar`.

**States:** closed → open → (optionally) asking-for-info → resolved (approved / rejected /
info-requested), each of which closes the dialog and shows an outcome line at the trigger.

**Accessibility:** `role="alertdialog"` with `aria-modal="true"` and `aria-labelledby` pointing at
the title, same as Phase 10A's Confirmation Flows — this is an interruption requiring a decision,
not a routine dialog. The consequence block pairs an info icon with full sentence text (never
color alone).

**Keyboard:** **Esc** closes without deciding · **Tab**/**Shift+Tab** are trapped inside the panel
· initial focus lands on **Request more info** (the least consequential action), never Approve,
so a stray Enter can't approve by accident · focus returns to the trigger on close.

**Content guidelines:** the rationale list states evidence/debate/judge findings as complete
sentences with real numbers (cohort counts, judge scores), not bullet fragments; the consequence
line states both outcomes ("Approving…", "Rejecting…") before either button is reachable.

**Implementation notes:** "Request more info" swaps the footer buttons for Back/Send in place
rather than closing and reopening the dialog — the rationale and consequence stay visible above
the question field the whole time.

**Tokens:** `--dialog-{bg,border,radius,pad,shadow}`, `--overlay-scrim`, `--overlay-blur`,
`--fb-info-{bg,border,text,icon}`, `--size-avatar`, `--btn-primary-*`, `--btn-secondary-*`,
`--btn-ghost-*`, `--field-*` (the info-request textarea).

**Do** show the rationale and consequence before either button is reachable by keyboard. **Don't**
default focus to Approve — the safest action on accidental activation should never be the one that
commits something.

## Notification Strategy

**Purpose:** a decision matrix for which of four existing notification components to reach for —
not a new component. Getting this choice wrong (e.g. a blocking dialog for a routine sync
completion) trains users to dismiss interruptions without reading them.

**When to use this decision, not a component:** whenever a new event needs surfacing and it isn't
already obvious which of the four fits — check blocking-ness, lifetime, and scope in that order.
**When not to use:** don't invent a fifth notification shape for an edge case; every real
ProductAgents event (sync completed, run degraded, invalid token, unsaved edit) maps onto one of
these four.

**Anatomy — the matrix:**

| Pattern | Blocking? | Lifetime | Scope |
|---|---|---|---|
| Toast | No | Auto-dismiss (~6s) or manual close | Global — app-wide event |
| Banner | No | Persists until dismissed or resolved | Page or section |
| Inline message | No | Persists while the condition holds | One field or row |
| Blocking dialog | Yes | Until a decision is made | The whole task/flow |

**Anatomy — the four components:** Toast (`.fbk-toast`, stacked, auto-dismissing, timer bar) for a
background event the user doesn't need to act on right now (a connector finished syncing). Banner
(`.fbk-banner`) for a condition that affects the whole page/section until resolved (a run
completed degraded). Inline message (`.fbk-inline`) for feedback scoped to exactly one field or
row, appearing and clearing with that field's own state (a rejected connector token, until
reconnected). Blocking dialog (locally, `.p10c-modal`) for the rare case the user genuinely cannot
proceed without deciding (discarding an unsaved edit).

**Variants:** n/a as a single control — the four matrix rows (Toast/Banner/Inline/Blocking
dialog) are the decision's options, not variants of one component; each is documented in its own
phase (Phase 3E for Toast/Banner/Inline, Phase 10A/10C for the blocking dialog).

**Sizes:** n/a — this pattern is a decision matrix, not a component with its own size axis; each
of the four notification components' sizing is documented in its own phase.

**States:** each component's own lifecycle governs it independently — a toast's timer, a banner's
dismiss/restore, an inline message's tie to its field's validity, a dialog's open/resolved. The
matrix itself has no state; it's a lookup, not a widget.

**Accessibility:** toast region is `role="status" aria-live="polite"`; banners use `role="alert"`
(warning/error) so assistive tech announces them without user action; inline messages are tied to
their field via `aria-describedby` and `aria-invalid`; the blocking dialog is `role="alertdialog"`
with the same focus-trap as Permission Requests. Every kind pairs its icon with text — never color
alone.

**Keyboard:** toast/banner dismiss buttons and the inline "Reconnect" action are plain `<button>`s
in tab order; the blocking dialog gets the same Esc/trap/restore as every other dialog in this
system.

**Content guidelines:** each of the four example messages is real ProductAgents copy voice — a
concrete cause ("Token rejected — reconnect the GitHub connector.", "Two analysts fell back to
scenario evidence — read the report before approving."), never a generic status phrase; see
Phase 3E for the shared `.fbk-*` copy conventions those components already document.

**Tokens:** all four reuse Phase 3E's `--fbk-*` component tokens (`--fbk-bg/border/text/icon` per
`.fbk-k-*` kind, `--fbk-toast-dwell`, `--fbk-timerbar-height`) — no new tokens introduced. The
blocking-dialog example reuses the same `--dialog-*`/`--overlay-*` tokens as Permission Requests.

**Do** pick the least-interruptive pattern that still gets the message across — most events are a
toast or an inline message, not a dialog. **Don't** reach for a blocking dialog just because a
message feels important; importance and blocking-ness are different axes; only gate the ones
where the user truly cannot proceed without a decision.

---

### Notes / deliberate simplifications
- The Error Recovery demos use fixed-cadence `setTimeout`s and deterministic outcomes (first
  attempt fails, every retry succeeds) to keep the recovery *shape* legible — the real connector
  sync and decision run report outcomes through `ConnectorService`/`runner.py`'s actual event
  stream, which this gallery doesn't have wired up.
- The Permission Requests dialog's "Request more info" flow ends the interaction locally (a status
  line); the real `human_approval` interrupt/resume cycle round-trips through the graph
  (`Command(resume=...)`), which this gallery doesn't simulate.
- The notification matrix intentionally reuses `.fbk-*` markup verbatim (including its icon
  sizing classes, `.fbk-ico`/`.fbk-ico--inline`) rather than wrapping it in `.p10c-*` chrome, per
  this task's brief — the pattern being demonstrated is the choice of component, not a new one.
