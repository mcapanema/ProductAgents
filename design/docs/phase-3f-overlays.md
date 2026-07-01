# Phase 3F · Overlays

Surfaces that float above the page. All stacking comes from `--z-*` tokens; all
color/spacing/radius/motion from the semantic + component token layers. In the
styleguide every overlay is contained inside a `position: relative;
overflow: hidden` `.ov-stage` so the scrim covers only the preview box — in the
product these surfaces portal to `<body>` with `position: fixed` (only the
containment differs, never the tokens or markup).

Shared keyboard/focus engine: `useOverlay(open, onClose)` — on open it stores
the active element, moves focus into the panel, traps Tab inside it, closes on
**Esc**, and **restores focus** to the trigger on close. Menus add roving
arrow-key focus (`onMenuKey`).

React API: not yet productized — each component here is a
`design/styleguide/src/phase3/` demo; a stable public API is defined when it
migrates to `desktop/src/ui/`.

---

## Modal / Dialog
- **Purpose:** A focused, blocking task over a dimmed scrim.
- **When not to use:** non-blocking supplementary content (filters, hints) —
  use Popover; details that should keep the underlying list visible — use Drawer.
- **Variants:** `sm` / `md` / `lg` (`--width-dialog-{sm,md,lg}`). Header (title +
  optional subtitle + close), scrollable body, right-aligned footer actions.
- **States:** open / closed; enter via `ov-pop` keyframe; hover/focus on close + actions.
- **Keyboard:** Esc closes · Tab/Shift+Tab trapped within the panel · focus lands
  on the first focusable, returns to the trigger on close.
- **Accessibility:** `role="dialog"` `aria-modal="true"` `aria-labelledby` →
  the title id. Scrim click closes.
- **Stacking:** scrim `--z-overlay`, panel `--z-modal`.
- **Tokens:** `--dialog-{bg,border,radius,pad,shadow}`, `--overlay-scrim`,
  `--overlay-blur`, `--width-dialog-*`, `--transition`/`--dur`/`--ease`.

## Drawer (edge sheet)
- **Purpose:** A right/left inspector that keeps the underlying list in view.
- **Variants:** `--right` / `--left`; width `--width-inspector`.
- **States:** open/closed; slides via `ov-slide-r` / `ov-slide-l`.
- **Keyboard:** identical to Modal (Esc, focus trap, restore).
- **Accessibility:** `role="dialog"` `aria-modal="true"` `aria-label`.
- **Stacking:** scrim `--z-overlay`, sheet `--z-modal`.
- **Tokens:** `--dialog-*`, `--elevation-overlay`, `--width-inspector`, `--overlay-*`.

## Popover
- **Purpose:** Anchored, non-modal free content (filters, hints).
- **Variants:** with / without arrow (`.ov-arrow--top`).
- **States:** open/closed; `ov-pop` enter.
- **Keyboard:** Esc closes (handler on the trigger); not focus-trapped (non-modal).
- **Accessibility:** trigger `aria-haspopup="dialog"` + `aria-expanded`; panel
  `role="dialog"` `aria-label`. Transparent `.ov-catch` closes on outside click.
- **Stacking:** click-catcher `--z-dropdown`, panel `--z-popover`.
- **Tokens:** `--popover-{bg,border,radius,pad,shadow}`, `--ov-arrow-size`, `--ov-menu-width`.

## Context / Dropdown Menu
- **Purpose:** A list of actions on a target.
- **Variants:** items, separators (`.ov-menu-sep`), keyboard shortcuts, submenu
  hint (trailing caret + `aria-haspopup`), disabled item, **destructive** item.
- **States:** hover / focus / disabled (`aria-disabled`) / destructive.
- **Keyboard:** Esc closes · ArrowUp/Down + Home/End move focus between items.
- **Accessibility:** `role="menu"` + `role="menuitem"`; disabled items
  `aria-disabled` + `tabindex="-1"`. Destructive item = danger color **plus** a
  trash icon **plus** the word "Delete" (1.4.1 — color is never the only channel).
- **Stacking:** catcher `--z-dropdown`, menu `--z-popover`.
- **Tokens:** `--popover-*`, `--surface-hover`, `--fb-error-bg`, `--text-error`, `--text-code`.

## Tooltip
- **Purpose:** A terse label tied to a control.
- **Variants:** single (top-anchored, with tail).
- **States:** hidden → shown after a dwell (`--ov-tooltip-delay`).
- **Keyboard:** opens on `:focus-visible` / `:focus-within` as well as hover;
  CSS-only, so no trap — pointer-events disabled.
- **Accessibility:** `role="tooltip"` + `aria-describedby` from the trigger.
- **Stacking:** `--z-tooltip` (always topmost).
- **Tokens:** `--tooltip-{bg,text,radius,pad-x,pad-y,font}`, `--ov-tooltip-delay`, `--ov-arrow-size`.

## Hover Card
- **Purpose:** A richer preview-on-hover (agent/entity summary).
- **Variants:** avatar + title + body + stat row; width `--ov-hovercard-width`.
- **States:** hidden → shown after a dwell on hover or focus-within.
- **Keyboard:** opens on `:focus-within` (Tab to the trigger); not focus-trapped.
- **Accessibility:** `role="dialog"` `aria-label`; trigger `aria-describedby`.
- **Stacking:** `--z-popover`.
- **Tokens:** `--popover-*`, `--width-inspector`, `--size-avatar`, `--surface-selected`, `--text-link`.

## Command Dialog (⌘K)
- **Purpose:** A centered command surface — the dialog shell of the Command Palette.
- **Variants:** search input (with `Esc` kbd), grouped command rows, shortcuts.
- **States:** open/closed; selected row (`aria-selected`); hover/focus rows.
- **Keyboard:** Esc closes · focus opens on the **input** (not the first row) ·
  Tab trapped within the dialog.
- **Accessibility:** `role="dialog"` `aria-modal`; list `role="listbox"` with
  `role="option"` rows.
- **Stacking:** scrim `--z-overlay`, dialog `--z-modal`.
- **Tokens:** `--dialog-*`, `--overlay-*`, `--width-dialog-md`, `--surface-selected`, `--text-code`.

## Confirmation Dialog
- **Purpose:** Confirm a consequential action; **destructive** sub-variant for
  irreversible ones.
- **Variants:** `info` (neutral) · `danger`. Danger adds a warning medallion and a
  tinted consequence block spelling out the exact effect.
- **States:** open/closed; primary vs danger confirm button.
- **Keyboard:** Esc closes · focus trap · focus restore.
- **Accessibility:** `role="alertdialog"` `aria-modal` `aria-label`. Destructive
  intent carried by **three** channels — danger color, warning/trash icons, and an
  explicit "Delete workspace" label + consequence text (1.4.1).
- **Content:** the consequence block names exact scope (real counts/entity
  names, e.g. "142 decisions, 9 connectors"), never a vague "This will delete
  data"; the confirm button repeats the action + target ("Delete workspace"),
  never a generic "Confirm".
- **Do** put Cancel before the destructive confirm in DOM order, so the
  focus-trap's initial focus (first focusable) lands on Cancel, not Delete —
  a stray Enter can't destroy anything. **Don't** default focus to the
  destructive action.
- **Stacking:** scrim `--z-overlay`, panel `--z-modal`.
- **Tokens:** `--dialog-*`, `--btn-danger-*`, `--fb-error-{bg,border,text,icon}`,
  `--fb-info-bg`, `--size-avatar`.

---

### Notes / deliberate simplifications
- Overlays are **contained, not portalled** in the styleguide (scrim scoped to
  `.ov-stage`); the product wraps the identical markup in a `position: fixed`
  portal. Zero token/markup change between the two.
- The submenu is shown as a **hint** (caret + `aria-haspopup`), not a working
  fly-out — the styleguide documents the affordance; the live menu wires the
  nested surface.
- Tooltip and hover card are **CSS-only** (hover + focus), so they need no JS,
  state, or focus trap.
