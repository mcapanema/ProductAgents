# Phase 3C — Forms

The input vocabulary of the Instrument: buttons, fields, choices, pickers. Every
rule consumes the token layer (`semantic.css` + `components.css` + the active
theme), so the whole set flips across `[data-theme]` and `[data-density]` with
zero markup change. Validation is never color-only — each state pairs a hue with
an inline SVG icon **and** a message (WCAG 1.4.1). All controls are real,
focusable elements with `:focus-visible` rings, label association, and
`aria-*` wiring.

Files: `styleguide/src/phase3/Phase3Forms.tsx` · `phase3c-forms.css` (prefix `fm-`).

---

## Button
- **Purpose:** trigger actions. One accent (primary) CTA per view; danger is the only other filled variant.
- **Variants:** primary · secondary · ghost · danger · icon (square, uniform per size tier; all four variants available) · leading-/trailing-icon · toggle (`aria-pressed`) · link · block (full-width) · loading (spinner).
- **Layout/order note:** the gallery's "interaction states" row shows default / hover / pressed / focus / disabled side-by-side via forced-state classes (the real pseudo-classes still drive on pointer + keyboard).
- **Sizes:** sm (`--control-sm`) · md (`--control-md`, default) · lg (`--control-lg`); type stays `--text-button` across sizes.
- **States:** default · hover (`-bg-hover`) · active (`-bg-pressed`) · focus · disabled (`--state-disabled-*`) · loading (`--state-loading-opacity` + `<span class="fm-spinner">`).
- **Keyboard:** native `<button>` — Tab to focus, Enter/Space to activate. Toggle latches via `aria-pressed`.
- **Accessibility:** icon buttons require `aria-label`; loading buttons set `aria-busy`; spinner honors `prefers-reduced-motion`.
- **Tokens:** `--btn-*` (height/radius/pad/gap/font/transition + per-variant bg/text/border), `--fm-spinner-*`, `--fm-underline-offset`, `--focus-ring-*`.

## Text Input
- **Purpose:** single-line free text. **Sizes:** `--field-height` (md). **States:** default · hover · focus · filled · disabled · invalid (`aria-invalid`) · success (`data-valid`).
- **Keyboard / a11y:** `<label htmlFor>` association; help via `aria-describedby`.
- **Tokens:** `--field-*`, `--border-width-default`, `--focus-ring-*`.

## Search Input
- **Purpose:** filter; leading magnifier + trailing clear. **States:** clear button appears only when non-empty.
- **Keyboard / a11y:** focus lands on the inner input; the `.fm-affix` shell shows the ring via `:focus-within`; clear button has `aria-label`.
- **Tokens:** `--field-*`, `--gap-inline`, `--text-tertiary`.

## Password Input
- **Purpose:** secret with a reveal toggle (`aria-pressed` eye / eye-slash).
- **Keyboard / a11y:** toggle is a real button with `aria-label`; switches `type` text↔password.
- **Tokens:** `--field-*`, `--icon-lg` (the inline icon button).

## Number Input (stepper)
- **Purpose:** bounded integer with a right-edge increment/decrement column.
- **Keyboard / a11y:** native `type=number` (arrow keys); stepper buttons are labelled and clamp at zero.
- **Tokens:** `--field-*`, `--icon-lg`, `--icon-xs` (caret glyphs).

## Text Area
- **Purpose:** multi-line rationale; vertical resize. **Tokens:** `--field-*`, `--fm-textarea-min` (`--space-80`), `--lh-normal`.

## Select (native-styled)
- **Purpose:** single choice from a short list. Native `<select>` with `appearance:none` and an overlaid caret (`pointer-events:none`).
- **Keyboard / a11y:** full native keyboard + screen-reader behavior retained.
- **Tokens:** `--field-*`, `--fm-caret-room` (`calc(--field-pad-x*2 + --icon-sm)`).

## Combobox (typeahead)
- **Purpose:** filter-as-you-type then pick. `role="combobox"` + `aria-expanded`/`aria-controls`; list is `role="listbox"`, options `role="option"`.
- **Keyboard / a11y:** options are real `<button>`s (Tab/Enter operable); selected option carries a check glyph. *ponytail:* arrow-key roving within the open list is left to the product wiring — options are individually focusable, so the list is operable without it.
- **Tokens:** `--fm-listbox-*`, `--fm-option-*`, `--surface-selected`, `--z-dropdown`.

## Multi-select (token chips)
- **Purpose:** pick several; selections render as removable chips inside the field.
- **Keyboard / a11y:** chip remove buttons are labelled (`Remove X`); list is `aria-multiselectable`; each option shows a checkbox marker.
- **Tokens:** `--chip-*`, `--surface-selected`, `--accent`, `--fm-listbox-*`.

## Checkbox (+ indeterminate)
- **Purpose:** binary / mixed. `appearance:none` box with an inline-SVG check or minus overlay (indeterminate set via DOM property/ref).
- **States:** default · hover · focus · checked · indeterminate · disabled.
- **Tokens:** `--fm-check-*`, `--border-width-strong`, `--radius-xs`.

## Radio (group)
- **Purpose:** one-of-N. `role="radiogroup"` + `aria-labelledby`; inner dot is a scaled fill.
- **Tokens:** `--fm-check-*`, `--radius-full`, `--dur-fast`/`--ease-standard`.

## Toggle Switch
- **Purpose:** instant on/off setting (not form submit). `role="switch"` + `aria-checked`; thumb slides via a `left` transition (collapses under reduced motion through the duration tokens).
- **Tokens:** `--fm-switch-*`, `--radius-pill`, `--accent`, `--elevation-raised`.

## Slider
- **Purpose:** single value with a measured numeric readout (mono, tabular-nums). Native `type=range`; filled track via a value-driven gradient (`--fm-slider-pct` set inline).
- **Keyboard:** arrows / Home / End / Page Up-Down (native).
- **Tokens:** `--fm-slider-*`, `--text-terminal`, `--border-width-focus`.

## Date / Time Picker
- **Purpose:** styled trigger + static calendar/time popover (no date lib — proves the surface). Days are `<button>`s; selected = accent, today = strong border, outside-month dimmed + `tabIndex=-1`.
- **Keyboard / a11y:** trigger `aria-haspopup`; calendar `role="dialog"`; day cells focusable and labelled by their number; time uses native `type=time`.
- **Tokens:** `--fm-cal-*`, `--field-*`, `--popover-*`, `--accent`.

## File Upload
- **Purpose:** dropzone (a `<label>` wrapping a visually-hidden `type=file`) + file list with size + remove. Drag-over flips to the active token set.
- **Keyboard / a11y:** the label is keyboard-reachable and opens the native picker; remove buttons labelled; input is `.fm-dz-input` (clip-rect hidden, not `display:none`, so it stays focusable).
- **Tokens:** `--fm-dropzone-*`, `--radius-card`, `--border-width-strong`.

## Form Field · Label · Help Text · Validation Message
- **Purpose:** the wrapper binding label → control → help/error. `.fm-label` (medium-weight body-s, not a tracked eyebrow), `[data-required]` adds a red asterisk; `.fm-help` is caption/tertiary; `.fm-msg--{error,success,warning}` each pair `--fb-*-text` + `--fb-*-icon` with an inline icon and message.
- **Accessibility:** help/error linked via `aria-describedby`; invalid via `aria-invalid`; **color is never the only channel** — every validation state carries an icon and text.
- **Tokens:** `--fm-label-font` (`--text-body-s`), `--text-caption`, `--fb-{error,success,warning}-{text,icon}`, `--text-error` (required asterisk).

---

### New tokens (all composed from existing tokens, declared at the top of `phase3c-forms.css`)
`--fm-underline-offset` · `--fm-spinner-{size,weight,track,dur}` · `--fm-check-{size,radius,bg,border,border-hover,on-bg,on-border,mark}` · `--fm-switch-{h,w,thumb,pad,track-off,track-on,thumb-bg}` · `--fm-slider-{track-h,thumb,track-bg,fill,thumb-bg,thumb-border}` · `--fm-textarea-min` · `--fm-caret-room` · `--fm-listbox-{bg,border,radius,shadow,maxh}` · `--fm-option-{pad-y,pad-x}` · `--fm-dropzone-{bg,bg-active,border,border-active,pad,icon}` · `--fm-cal-{cell,gap}` · `--fm-label-font` · `--fm-field-gap`.

Each is a one-line alias/`calc()`/`color-mix()` over a primitive or semantic token, so retargeting (e.g. switch geometry) happens in one place and theming/density still flow from the layers below. Nothing here required a value the token system couldn't express.
