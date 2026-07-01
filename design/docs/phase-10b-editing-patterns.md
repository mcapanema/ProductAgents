# Phase 10B — Direct-manipulation & editing patterns

Inline Editing, Keyboard-First Interactions, Drag-and-Drop, Selection, Bulk Actions, and
Undo/Redo — `src/phase10/Phase10BEditingPatterns.tsx` + `phase10b-editing-patterns.css`,
prefixed `p10b-`. Live gallery: `styleguide` → `Editing Patterns`.

**This is a patterns doc, not a component spec.** Like Phase 10A, this phase is about **when
and why** to reach for direct manipulation rather than a full-page form or a blocking dialog —
so each section leads with When to use / When not to use. Where a demo needs a button, field,
table, or kbd chip, it reuses the same tokens already established elsewhere (`.fm-*` form
chrome, `.nv-kbd`/`.nv-keys` shortcut chips, `.fbk-toast` snackbar chrome), re-declared locally
(`.p10b-*`) per the one-file-per-phase convention every prior phase module follows.

**Keyboard-first is non-negotiable here.** This group includes the two patterns most often
shipped mouse-only — drag-and-drop and multi-select — so both ship a working non-mouse path:
explicit move-up/move-down buttons sit next to the drag handle, and every selection checkbox
stays toggleable with Tab+Space whether or not anyone ever uses Shift+click.

Built only from the existing token layer (no new colors — `contrast.py` still reports 0
failures, both themes and CVD simulation). Icons are inline SVG (Phosphor-style,
`stroke="currentColor"`), defined locally in `Phase10BEditingPatterns.tsx`.

---

## Inline Editing

**Purpose:** edit a value where it lives — a title, a table cell — without navigating to a
separate edit form or page.

**When to use:** short, single-field values that belong to a row or header the user is already
looking at (an initiative's name, a roadmap item's owner). **When not to use:** multi-field
edits, anything needing validation against other fields, or values with consequences worth a
second look — those belong in a real form (or, for destructive consequences, the Confirmation
flows / Destructive actions patterns in Phase 10A).

**Anatomy:** a display state (value + a pencil icon that appears on hover/focus) → click or
Enter activates → an input replaces the display, scoped tightly to just that value, flanked by
explicit Save (check) and Cancel (×) icon buttons → committing shows a transient "Saved"
acknowledgment next to the value.

**States:** display → editing (input focused, draft state local until committed) → saved
(value updates, 2-second acknowledgment, then back to plain display). Cancel reverts to the
last-saved value without committing the draft.

**Accessibility:** the input carries an `aria-label` naming the field (`Owner for Bulk
actions`, not just `Owner`) since the visible label is the cell's column header, not a
`<label>` next to the input. The "Saved" acknowledgment is `role="status"` so it's announced
without stealing focus.

**Keyboard:** **Enter** commits (same as clicking Save) · **Escape** cancels and reverts ·
**blur** (clicking or tabbing away) also commits, matching the common rename-in-place
convention (Notion, Trello) — so there's no way to "lose" focus and leave the value stuck in a
half-edited state. The Save/Cancel buttons use `onMouseDown` `preventDefault` so clicking them
doesn't fire blur-commit before their own click handler runs.

**Tokens:** `--field-bg`, `--field-border-focus`, `--size-control`, `--pad-control-x`,
`--ai-done-text`, `--text-heading-4` (title variant), `--radius-control`.

**Do** keep the edit surface exactly the size of the value being edited — it should never
reflow the surrounding layout. **Don't** auto-save on every keystroke; commit only on an
explicit signal (Enter, Save, or blur) so a half-typed value is never persisted.

## Keyboard-First Interactions

**Purpose:** state the system's keyboard conventions once, in one place, instead of leaving
every team to reinvent (or forget) them per screen.

**When to use:** as a reference for anyone building a new screen or composite widget.
**When not to use:** n/a — these conventions apply everywhere; the question is never whether to
follow them, only how a given widget expresses them.

**Anatomy:** a conventions list (focus order, the `⌘K` command palette, arrow-key navigation,
focus rings) followed by one live composite-widget demo — a menu using a **roving tabindex**:
exactly one item is in the Tab sequence (`tabIndex={0}`) at a time, and arrow keys move which
one that is, rather than Tab stepping through every item.

**Grounding.** The `⌘K` command palette referenced here already exists — Phase 3B's
`.nv-palette` (the embedded omnibox, arrow-key + Enter operable, documented in that phase) and
Phase 3F's `.ov-command` (the modal it can also open). This doc cross-references rather than
rebuilds either; the roving-tabindex pattern they both use for arrow-key navigation is the same
one demoed here.

**States:** the menu's active item is both visually highlighted and the sole Tab stop;
activating one (Enter/click) shows what ran.

**Accessibility:** `role="menu"` / `role="menuitem"` and the roving-tabindex pattern (one
`tabIndex={0}`, the rest `-1`) are the standard ARIA Authoring Practices approach for composite
widgets — it keeps a single Tab stop for the whole widget (consistent with the rest of the
page's focus order) while arrow keys move freely inside it.

**Keyboard:** **↑/↓** move the active item · **Home/End** jump to the first/last item ·
**Enter** activates · focus rings are visible on every focusable element in this entire
gallery (and the whole design system) — Tab through any control on the page to see one; none
rely on color alone (1.4.1).

**Tokens:** `--focus-ring-width`, `--focus-ring-offset`, `--border-focus`, `--surface-hover`,
`--surface-raised`.

**Do** give every composite widget (menu, listbox, toolbar) exactly one Tab stop and move focus
inside it with arrow keys. **Don't** make Tab step through individual menu items — that breaks
the page's focus order and makes a 10-item menu a 10-Tab detour.

## Drag-and-Drop

**Purpose:** reorder a list by directly manipulating its items, for users who reach for a
mouse or trackpad.

**When to use:** reordering where position has meaning the user controls directly (dashboard
widget order, a kanban column's card order). **When not to use:** as the *only* way to reorder
— drag-and-drop has no accessible keyboard equivalent on its own (dragging requires sustained
pointer control many users can't provide), so it must always ship next to a keyboard
alternative, never instead of one.

**Anatomy:** a drag handle (grip icon, `cursor: grab`) → the item label → explicit **move
up**/**move down** icon buttons, always visible, doing the exact same reorder as a completed
drag. Both paths update the same list state and announce the same way.

**States:** idle → dragging (the dragged item dims to signal it's lifted; `aria-grabbed="true"`)
→ dropped (list re-orders) or move-button pressed (list re-orders immediately, no drag needed).

**Accessibility:** the move buttons are real `<button>` elements in normal tab order, disabled
at the top/bottom edge (`disabled` when already first/last) so their state alone communicates
the boundary. A visually-hidden `aria-live="polite"` region announces every move ("Moved
'Connector health' to position 2 of 4") for both the drag and the button path, since native
HTML5 drag-and-drop has no built-in screen-reader announcement.

**Keyboard:** **Tab** to a row's move buttons, **Enter**/**Space** to activate — this is the
*complete* alternative to dragging, not a degraded fallback; every reorder a mouse user can
perform, a keyboard-only user can perform identically, in the same number of list positions.

**Tokens:** `--surface-raised`, `--border-subtle`, `--radius-control`, `--state-disabled-opacity`
(dragged-item dim and disabled-button states share the token).

**Do** keep the move buttons visible at all times, not revealed only on hover — hover-only
controls are invisible to keyboard and touch. **Don't** ship drag-and-drop without them; a
mouse-only reorder control fails every keyboard and switch-device user outright.

## Selection

**Purpose:** let a user act on one or many rows in a list or table via an explicit checkbox
column, with mouse shortcuts for ranges.

**When to use:** any list where bulk operations make sense (feedback triage, connector
management, decision review queues). **When not to use:** lists with no bulk operation to
perform — an unused selection UI is pure visual noise.

**Anatomy:** a checkbox column (including a header "select all" checkbox, which goes
indeterminate when some-but-not-all rows are selected) → a visible count ("3 of 4 selected")
replacing the idle hint text once anything is selected.

**States:** none selected (idle hint shown) → partial (count shown, header checkbox
indeterminate) → all selected (header checkbox checked).

**Accessibility:** each row sets `aria-selected` to match its checkbox so assistive tech
reports selection state on the row, not just the checkbox. The header checkbox's indeterminate
state is set imperatively via a ref (`element.indeterminate = …`) since it isn't a settable JSX
prop. The selected-count text is `role="status"` so screen-reader users hear the count update
without it stealing focus.

**Keyboard:** **Tab** to any checkbox, **Space** toggles it — this alone reaches every row,
independent of any mouse modifier. **Shift+click** extends a contiguous range from the
last-toggled checkbox — a mouse *shortcut* for ranges, never the only way to multi-select.
**Ctrl/Cmd+click** toggles a single checkbox the same way a plain click does here, since a
checkbox's own semantics are already additive (it never clears its siblings) — the modifier
only matters on click surfaces that *aren't* checkboxes, where a plain click would otherwise
replace the whole selection.

**Tokens:** `--surface-selected` (selected-row background), `--accent` (checkbox
`accent-color`), `--text-tertiary` (column headers).

**Do** keep selection mechanics (checkbox, count, select-all) identical wherever they appear in
the product — Bulk Actions below reuses this exact mechanism. **Don't** make Shift-range the
only way to select more than one row; every row must stay individually reachable by keyboard.

## Bulk Actions

**Purpose:** the toolbar that appears once 1+ rows are selected, offering actions scoped to the
whole selection.

**When to use:** as the direct continuation of Selection above — the moment a selection becomes
non-empty. **When not to use:** don't surface bulk actions permanently (disabled, with a "select
rows first" tooltip) — replacing the idle state with the toolbar only when it's actionable keeps
the UI quiet until there's something to do.

**Anatomy:** a count ("3 selected") → the action buttons themselves (icon + label, scaled to
the action's severity — `secondary` for Archive, `danger` for Delete, same variants Phase 10A's
Destructive Actions established) → a **Clear** button, right-aligned, that empties the
selection without performing any action.

**States:** hidden (selection empty) → visible (selection non-empty; replaces the idle hint
text in the same vertical slot so the toolbar's appearance doesn't shift the table below it).

**Accessibility:** the toolbar is `role="toolbar"` with an `aria-label`, grouping its buttons
for assistive tech as one operable unit. Performing an action clears the selection and replaces
the count with a confirmation sentence ("Archived 3 items.") in the same `role="status"` slot
the idle hint occupied — one place to look, before and after.

**Keyboard:** every toolbar button is a normal focusable `<button>`; nothing here requires a
mouse beyond what Selection already requires to build the selection in the first place.

**Tokens:** `--surface-selected` (toolbar background — matches the selected-row tint, visually
tying the bar to the rows it acts on), `--border-focus` (toolbar border), `--btn-secondary-*`,
`--btn-danger-*`.

**Do** pair a bulk **Delete** with the Undo/Redo pattern below rather than a confirmation
dialog, when the action is reversible — that's the whole point of inline undo. **Don't** stack
a blocking dialog in front of a bulk action that could just be undone; see Phase 10A's
Confirmation Flows decision tree for the reversible-vs-irreversible call.

## Undo/Redo

**Purpose:** the reversible alternative to a blocking confirmation dialog — act immediately,
then offer a way back.

**When to use:** consequential-but-reversible actions (archiving, removing a connector,
deleting a row that can be restored) — this is exactly tier 2 of Phase 10A's Confirmation
Flows decision tree, the one that explicitly says "no dialog, act immediately, offer inline
undo." **When not to use:** irreversible or high-blast-radius actions — those still need Phase
10A's blocking confirmation; an undo toast that can't actually undo the damage is worse than no
safety net at all.

**Anatomy:** the action completes immediately (the connector disappears from the list) → a
toast appears in the corner of the contained stage (never the page, same containment Phase 10A
established for scrims/dialogs) with an icon, a sentence naming what happened, an **Undo**
button, and a depleting timer bar showing how long Undo remains available.

**States:** idle → pending-undo (toast visible, timer running) → either undone (item restored,
toast dismissed immediately) or expired (timer reaches zero, toast dismissed, action stands).

**Accessibility:** the toast is `role="status"` with `aria-live="polite"` so screen readers
announce it without interrupting whatever the user was doing. The Undo button is a real
`<button>`, not a link styled to look like one, and is reachable by Tab while the toast is
visible.

**Keyboard:** **⌘Z** (or **Ctrl+Z**) triggers Undo while the toast is visible — the document-level
listener is only attached while a pending action exists, so it can never hijack the browser's
native undo elsewhere on the page. **⌘⇧Z** (Redo) isn't wired into this demo: a single-shot undo
toast has nothing to redo until another undo happens — the same reasoning Gmail's "Undo Send"
follows. A multi-level undo/redo stack would wire `⌘⇧Z` to re-apply the most recently undone
action; that's beyond what one toast demonstrates.

**Tokens:** `--surface-floating`, `--toast-radius`, `--toast-shadow`, `--z-toast`,
`--ai-done-text` (toast icon), `--text-link` (Undo action), `--border-default` (timer-bar
track).

**Do** keep the undo window generous (this demo uses 6 seconds, matching Phase 3E's toast
dwell) and let any further action of the same kind replace the pending toast rather than
stacking a second one. **Don't** use an undo toast as cover for skipping the destructive-action
treatment in Phase 10A — if the data is actually gone once the timer expires, that's still a
deletion, and severity-appropriate affordances (danger color, an explicit cost statement) still
apply to the action that triggered it.
