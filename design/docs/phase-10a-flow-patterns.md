# Phase 10A — Flow & risk patterns

Confirmation Flows, Destructive Actions, Long-Running Operations, Multi-Step Workflows, and
Progressive Disclosure — `src/phase10/Phase10AFlowPatterns.tsx` + `phase10a-flow-patterns.css`,
prefixed `p10a-`. Live gallery: `styleguide` → `Flow Patterns`.

**This is a patterns doc, not a component spec.** Phase 3F already specs the overlay/dialog
*components* (`.ov-*`: modal, scrim, medallion, consequence block) and Phase 3C specs the form
*components* (`.fm-*`: fields, buttons, the danger variant). This phase is about **when and why**
to reach for those components — the decision a designer or engineer makes before a single pixel
is drawn — so each section below leads with When to use / When not to use rather than anatomy.
Where a demo needs a dialog or a field, it reuses the same tokens those phases established,
re-declared locally (`.p10a-*`) per the one-file-per-phase convention every prior phase module
follows (e.g. Phase 9's `.p9-btn` mirrors Phase 3E's `.fbk-btn` rather than importing it).

**Grounding.** The long-running operation patterns are drawn directly from the two real
ProductAgents operations that take seconds to minutes: a decision pipeline run (`evidence →
five analysts → debate → strategist → judge → risk → governance`, unknown duration —
indeterminate) and a connector sync (`ConnectorService.sync()`, a known item count — determinate).
The multi-step workflow demo mirrors adding a connector to `connectors.yaml` (type → configure →
review). The progressive-disclosure demo's "advanced settings" mirror real
`PRODUCTAGENTS_JUDGE_THRESHOLD` / `PRODUCTAGENTS_DEBATE_ROUNDS` env knobs.

Built only from the existing token layer (no new colors — `contrast.py` still reports 0
failures, both themes and CVD simulation). Icons are inline SVG (Phosphor-style,
`stroke="currentColor"`), defined locally in `Phase10AFlowPatterns.tsx`.

---

## Confirmation Flows

**Purpose:** decide whether an action needs a blocking "are you sure?" gate at all, before
reaching for a dialog component.

**When to use:** only for the third tier of the decision tree below — irreversible or
high-blast-radius actions (deleting a workspace, submitting a governance decision for review).
**When not to use:** trivial/reversible actions (skip confirmation — let the user act and learn
by doing) or consequential-but-reversible actions (archiving a project, removing a row — act
immediately and offer an inline undo instead; see the Undo/Redo pattern for that affordance).
Stacking a dialog in front of every destructive-sounding click trains users to click through it
without reading, which defeats the gate entirely.

**Anatomy:** medallion (info or danger) → title → one-sentence consequence → Cancel (ghost,
first in DOM order) → primary confirm action. Built from the same scrim/modal/medallion shell
Phase 3F's Confirmation Dialog component specs.

**States:** closed → open (scrim + panel enter) → confirmed or cancelled, both of which close the
dialog and return focus to the trigger.

**Accessibility:** `role="alertdialog"` with `aria-modal="true"` and `aria-labelledby` pointing
at the title; the dialog announces itself as an interruption, not a routine `dialog`.

**Keyboard:** **Esc** closes (same as Cancel) · **Tab**/**Shift+Tab** are trapped inside the
panel · focus lands on the first focusable element on open (Cancel, never the confirm action)
and returns to the trigger on close.

**Tokens:** `--dialog-{bg,border,radius,pad,shadow}`, `--overlay-scrim`, `--overlay-blur`,
`--width-dialog-sm`, `--fb-info-{bg,icon}`, `--size-avatar`, `--btn-primary-*`, `--btn-ghost-*`.

**Do** gate only the action that actually can't be walked back. **Don't** put a confirmation
dialog in front of something undo can handle — that's a tax on every user to protect against the
rare one who meant to cancel.

## Destructive Actions

**Purpose:** the visual and interaction conventions that make a delete/remove/revoke action
impossible to trigger by accident.

**When to use:** any action that destroys data or access with no path back — deleting a project,
revoking a credential, removing a connector and its synced history. **When not to use:** for
actions that are merely hard to repeat (re-running an evaluation costs time, not data) — those
get a plain confirmation, not the danger treatment; reserving red for genuine data loss keeps it
meaningful.

**Anatomy:** danger button (`.fm-btn--danger` / locally `.p10a-btn--danger`) as the trigger →
dialog with a warning medallion and an explicit consequence statement (counts, not just "this
cannot be undone") → a deliberate second step scaled to the blast radius: **type the resource
name** for the most catastrophic actions (deleting a project), or **an "I understand" checkbox**
for moderately catastrophic ones (revoking a key) → Cancel and the danger confirm action.

**States:** the confirm button stays disabled until its gate is satisfied (typed text matches
exactly, or the checkbox is checked) — there is no state where the destructive action is one
click away by default.

**Accessibility:** destructive intent is carried by three channels at once — danger color, a
trash/warning icon, and an explicit label ("Delete project", never just "Confirm") — never color
alone (1.4.1). The type-to-confirm input has a `<label>` naming the exact expected value.

**Keyboard:** same Esc/trap/restore as Confirmation Flows above. Critically, **Cancel is first in
DOM order**, so it — not the destructive action — receives initial focus when the dialog opens; a
stray Enter keypress can never trigger deletion.

**Tokens:** `--btn-danger-{bg,bg-hover,text}`, `--fb-error-{bg,border,text,icon}`, `--field-*`,
`--accent` (checkbox `accent-color`).

**Do** scale the friction to the damage — typed confirmation for the worst case, a checkbox for
the rest. **Don't** ever let the destructive button be the dialog's default-focused control.

## Long-Running Operations

**Purpose:** how the UI represents work that takes seconds to minutes, so the user always knows
whether it's still running, how long is left (if knowable), and how to back out.

**When to use:** any operation crossing roughly one second — a connector sync, a decision
pipeline run. **When not to use:** sub-second interactions, which need no progress affordance at
all (a spinner that flashes for 80ms reads as a glitch, not feedback).

**Anatomy — determinate** (a total is known, e.g. syncing N issues from a GitHub connector): a
track-and-fill progress bar with a live percentage, plus a status line. **Anatomy —
indeterminate** (duration is unknown, e.g. a decision run's five analysts + debate + judge): a
spinner plus a status line describing what's happening, not how long it'll take. Both keep the
trigger control **visible, disabled, and labeled with a spinner** while running — never hidden or
removed — and both expose a **Cancel** action for the duration of the run.

**States:** idle → running (trigger disabled + spinner; determinate also ticks the fill width and
percentage) → settled (success copy) or cancelled (back to idle immediately, no settle copy).

**Accessibility:** the determinate bar is `role="progressbar"` with `aria-valuenow/min/max` and an
`aria-label` naming the operation; the indeterminate status line is `role="status"
aria-live="polite"` so screen readers hear the state change once, not on every frame.

**Keyboard:** the trigger and Cancel are both real `<button>`s in normal tab order — no custom
key handling is needed because nothing here is a focus-trapped surface.

**Tokens:** `--ai-running`, `--ai-done`, `--gauge-track`, `--dur-slow`, `--ease-standard`,
`--radius-pill`. `prefers-reduced-motion` parks the spinner rotation and the fill-width
transition, matching every other animated state in this design system.

**Do** keep the trigger visible and disabled during the run so the user can see what's executing.
**Don't** swap the trigger for a bare spinner with no label — that erases the connection between
the click and the work it started.

## Multi-Step Workflows

**Purpose:** a stepper for input that's naturally sequential, so a long form doesn't have to be
validated and submitted all at once.

**When to use:** setup flows with a real order dependency — configuring a new connector (pick a
type before you can configure it; configure before you can review it). **When not to use:** for
forms whose fields don't depend on each other; a stepper there only adds clicks. If the whole
form fits one screen and any field can be filled in any order, use a single page instead.

**Anatomy:** a step indicator (number/check dot + label + connecting line, one entry per step) →
a card holding the current step's fields → a footer with Back (disabled on the first step) and
Next/primary-action (disabled until the step's required field is filled).

**States:** each step indicator entry is `data-state="upcoming"|"current"|"done"`. Per-step
validation gates Next — the connector-type step requires a selection, the configure step requires
a non-empty value — so the user can't reach Review with incomplete input. **Going back preserves
every value already entered**: state lives in the wizard's parent component, not the step, so
nothing resets on Back.

**Accessibility:** the step indicator has an `aria-label` naming the overall flow; "done" steps
are conveyed by a check glyph **and** position **and** the label text, not green-vs-grey color
alone.

**Keyboard:** Back/Next/type-option buttons are plain `<button>`s in document order — Tab moves
forward through the current step's fields, Shift+Tab back, no trap (this is a normal page region,
not an overlay).

**Tokens:** `--accent`, `--ai-done`, `--card-bg-raised`, `--card-border`, `--card-radius`,
`--field-*`, `--btn-*`.

**Do** keep every entered value in state that survives Back. **Don't** let Next advance past a
step with missing required input — that just moves the validation error to a worse place (Review,
or the backend).

## Progressive Disclosure

**Purpose:** show-more / accordion / "advanced settings" controls that hide detail most people
don't need by default, without removing it.

**When to use:** settings or content with a clear default-vs-power-user split (most initiatives
never touch the judge threshold or debate-round count) or independent Q&A-style content where
showing everything expanded would be noisy. **When not to use:** for the field or fact someone
needs to complete the primary task — if most users open it every time, it isn't "advanced," it's
just hidden, and it belongs in the default view.

**Anatomy:** a text trigger with a leading chevron that rotates on open → the revealed content,
indented under the trigger. The same `Disclosure` primitive backs two demos: a single "Advanced
settings" toggle next to two always-visible fields, and a multi-item accordion where each item
expands independently (not single-open) — both are the same control, used once or in a list.

**States:** collapsed (default) / expanded, per-item — there is no "all expanded" or "all
collapsed" coupling between accordion items in this pattern.

**Accessibility:** the trigger is a real `<button>` with `aria-expanded` reflecting its state and
`aria-controls` pointing at the panel's id — the chevron rotation is decorative reinforcement,
`aria-expanded` is the channel assistive tech actually reads.

**Keyboard:** the trigger is reachable and operable with Tab + Enter/Space (native `<button>`
semantics); no custom key handling needed.

**Tokens:** `--text-link`, `--dur-fast`, `--ease-standard` (chevron rotation), `--surface-raised`,
`--border-subtle`, `--radius-control` (accordion item shell).

**Do** default to collapsed only when most users genuinely don't need the content. **Don't**
convey expanded/collapsed with the chevron rotation alone — `aria-expanded` is load-bearing, not
decorative.

---

### Notes / deliberate simplifications
- The confirmation/destructive dialog chrome and its focus-trap hook (`useOverlay`) are
  re-declared locally rather than imported from Phase 3F, matching the self-containment
  convention every prior phase module already follows.
- Long-running demos use a fixed-cadence `setInterval`/`setTimeout` to simulate progress — the
  real connector sync and decision run report progress through `ConnectorService`/`runner.py`'s
  actual event stream, which this gallery doesn't have wired up.
- The wizard demo has exactly the steps needed to show validation-and-back-preservation (3); it
  is not a full connector-configuration form.
