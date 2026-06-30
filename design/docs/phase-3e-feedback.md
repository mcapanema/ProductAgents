# Phase 3E — Feedback

Feedback, progress, and status components for the ProductAgents styleguide.
Files: `styleguide/src/phase3/Phase3Feedback.tsx` + `phase3e-feedback.css`
(class prefix `fbk-`). Token-only; both themes + both densities adapt with zero
markup change. Colour is never the only channel — every variant pairs its hue
with an inline SVG icon + a text label. Every animation has a
`prefers-reduced-motion` fallback.

New tokens (in `:root` at the top of the CSS, composed from existing roles):
`--fbk-bg/surface/border/text/icon` (per-variant colour group, defaulting
neutral), `--fbk-toast-width` (= `--width-inspector`), `--fbk-toast-gap`,
`--fbk-toast-dwell` (`6000ms`, a *new* timing primitive above the 560ms motion
scale — auto-dismiss dwell, no existing base to compose from; JS timeout
matches), `--fbk-timerbar-height` (= `--border-width-focus`),
`--fbk-progress-height` (= `--gauge-height`), `--fbk-progress-fill` (=
`--accent`), `--fbk-progress-live` (= `--ai-running`), `--fbk-ring-size` (=
`--space-48`), `--fbk-ring-track` (= `--ai-confidence-track`),
`--fbk-spinner-size` (= `--icon-md`), `--fbk-skeleton-base` (=
`--surface-sunken`), `--fbk-skeleton-sheen` (= `--surface-hover`),
`--fbk-state-icon` (= `--space-48`), `--fbk-state-max` (= `--measure-prose`),
`--fbk-overlay-scrim` (= `--overlay-scrim`), `--fbk-overlay-blur` (=
`--blur-scrim`).

The four colour groups are set once by `.fbk-k-{success,warning,error,info}`
(mapping the theme `--fb-*-{bg,surface,border,text,icon}` sets onto the local
`--fbk-*` handles) and reused by alert, banner, inline, toast, and status state.

---

## Alert
- **Purpose** — boxed, ground-tinted message with title + body, optional action and dismiss.
- **Variants** — success / warning / error / info; with / without action; with / without dismiss.
- **States** — static; dismissible (focusable close button removes it; "Restore alert" re-mounts in the demo); action + close have hover + focus-visible.
- **Keyboard** — action and close are real `<button>`s, in tab order; close has `aria-label`.
- **Accessibility** — error/warning → `role="alert"` (assertive); success/info → `role="status"`. Icon + title carry meaning beyond hue.
- **Motion** — none beyond token surface transitions (auto-collapse under reduced motion).
- **Tokens** — `--alert-pad/-radius/-border-width/-icon-size`, `--fbk-*` group, `--text-title/-body-s`, `--gap-inline`, `--control-sm`.

## Toast
- **Purpose** — transient notification; stacks; auto-dismisses on a timer bar.
- **Variants** — success / info / warning / error (4 rotating samples).
- **States** — entering (slide+fade); dwelling (timer bar shrinks); dismissed (auto after `--fbk-toast-dwell`, or via close button / "Clear all").
- **Keyboard** — close button per toast (`aria-label`), in tab order.
- **Accessibility** — region is `role="status"` + `aria-live="polite"` + `aria-relevant="additions"`; icon + title beyond hue.
- **Motion** — `fbk-toast-in` (enter), `fbk-timer` (scaleX bar). **Reduced motion:** both parked — bar stays full (muted), enter is instant; JS timeout still dismisses.
- **Tokens** — `--toast-shadow/-radius`, `--surface-floating`, `--fbk-toast-width/-gap/-dwell`, `--fbk-timerbar-height`.

## Banner
- **Purpose** — full-width, page/run-level condition (degraded, offline).
- **Variants** — warning ("Run degraded"), error ("Offline").
- **States** — static + action buttons (hover/focus).
- **Keyboard** — action buttons in tab order.
- **Accessibility** — `role="alert"` (degraded) / `role="status"` (offline); accent left edge + icon + label.
- **Motion** — none (surface transitions only).
- **Tokens** — `--fbk-*` group, `--border-width-focus` (left edge), `--pad-card`, `--text-body-s`.

## Inline message
- **Purpose** — compact, single-line, form-adjacent validation/help.
- **Variants** — error / success / warning / info.
- **States** — static.
- **Keyboard** — non-interactive (associate with its field via `aria-describedby` in product use).
- **Accessibility** — inline icon + text; `--size-icon-inline` glyph aligns to caption text.
- **Motion** — none.
- **Tokens** — `--text-caption`, `--size-icon-inline`, `--gap-inline`, `--fbk-*` group.

## Progress — linear
- **Purpose** — task progress; determinate (measured) and indeterminate (unknown duration).
- **Variants** — determinate (indigo `--accent`, numeric %); indeterminate (amber `--ai-running` = live, "working…").
- **States** — value driven live by −10/+10 buttons; width transitions.
- **Keyboard** — control buttons in tab order; bar itself is `role="progressbar"` with `aria-valuenow/min/max` (determinate only).
- **Accessibility** — numeric reading always shown next to the bar; colour reinforces.
- **Motion** — `fbk-indeterminate` slide. **Reduced motion:** parked to a static full-width muted bar.
- **Tokens** — `--gauge-track/-radius`, `--fbk-progress-height/-fill/-live`, `--text-terminal` (tabular figures).

## Progress — circular & spinner
- **Purpose** — compact determinate ring (with centre numeral) and unknown-duration spinner.
- **Variants** — ring (determinate, indigo); spinner sm / md / lg (amber = loading).
- **States** — ring offset transitions with the shared `pct`.
- **Keyboard** — ring is `role="progressbar"` with values; spinner is `role="status"` + `aria-label`.
- **Accessibility** — ring numeral always rendered; spinner has a label.
- **Motion** — `fbk-spin` rotate. **Reduced motion:** rotation off, arc lengthened (`60 40`) so the static state reads intentional, not broken.
- **Tokens** — `--fbk-ring-size/-track`, `--fbk-progress-fill`, `--fbk-spinner-size`, `--icon-sm/-md/-xl`, `--ai-running`.

## Skeleton
- **Purpose** — content placeholders during load.
- **Variants** — text line, line, avatar, card (composed).
- **States** — shimmering (loading).
- **Keyboard** — n/a (decorative; mark the live region `aria-busy` in product use).
- **Accessibility** — purely visual; no colour-coded meaning.
- **Motion** — `fbk-shimmer` travelling sheen. **Reduced motion:** shimmer removed, flat `--fbk-skeleton-base` fill.
- **Tokens** — `--fbk-skeleton-base/-sheen`, `--avatar-md`, `--radius-control/-pill`, `--card-*`.

## Status states (empty / error / success / warning)
- **Purpose** — full-block state: hero icon + heading + description + action.
- **Variants** — empty (neutral, tray icon), success, warning, error.
- **States** — static; primary + optional secondary action.
- **Keyboard** — action buttons in tab order with focus-visible ring.
- **Accessibility** — error → `role="alert"`, others `role="status"`; distinct icon per state; copy carries the message.
- **Motion** — none.
- **Tokens** — `--fbk-state-icon/-max`, `--surface-sunken`, dashed `--border-subtle`, `--text-heading-4/-body-s`, `--btn-*`.

## Loading overlay
- **Purpose** — scrim + spinner over a *contained* region; dims and inert-ifies content beneath.
- **Variants** — one (region-scoped).
- **States** — idle / loading (toggled by "Run evaluation", auto-clears after ~2.2s).
- **Keyboard** — trigger button in tab order; underlying content `aria-hidden` while loading.
- **Accessibility** — overlay carries the labelled spinner + text; content marked `data-loading`/`aria-hidden`.
- **Motion** — `fbk-fade` in. **Reduced motion:** fade off (appears instantly). Backdrop blur via `--blur-scrim`.
- **Tokens** — `--overlay-scrim`, `--blur-scrim`, `--z-overlay`, `--state-loading-opacity`, `--card-*`.

---

### Self-review checklist
- Every alert / toast / banner / inline / state pairs colour with an icon **and** a text label (1.4.1). ✓
- Dismissible items (alert, toast) have a focusable close button with `aria-label`. ✓
- Toasts: `role="status"` + `aria-live`; interrupting alerts/banners: `role="alert"`. ✓
- All animations (toast enter + timer, indeterminate bar, spinner, skeleton shimmer, overlay fade) have explicit `prefers-reduced-motion` fallbacks. ✓
- Token-only — no raw colour/space/radius/size/duration/z literals except the single justified `--fbk-toast-dwell` timing primitive. ✓
