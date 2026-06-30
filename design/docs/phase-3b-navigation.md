# Phase 3B — Navigation

Wayfinding & command surfaces for the resource-explorer IA. Every component is
built from the token layer only, works in both themes and both densities with
zero markup change, is keyboard-operable, and never signals state by color
alone. Gallery: `styleguide` → "3B · Navigation". Source:
`src/phase3/Phase3Navigation.tsx` + `phase3b-navigation.css` (prefix `nv-`).

---

## Sidebar Nav
- **Purpose:** the resource spine of the app — Run, Workflows, Sessions, Decisions, Connectors, Prompts, Settings.
- **When to use:** primary navigation in the expanded shell. **Not** for in-page facet switching (use Tabs).
- **Anatomy:** `nav[aria-label]` → list of `button` items (icon + label + optional live dot).
- **States:** default · hover · selected (`aria-current="page"`). Selected = tinted ground **+** accent left-marker **+** accent icon **+** semibold — four channels, never color alone.
- **Keyboard:** Tab between items; Enter/Space activates. Focus ring inset on `:focus-visible`.
- **A11y:** `aria-current="page"` on the active item; the live dot has `role="img"` + label "run in progress".
- **Tokens:** `--nav-item-*`, `--width-sidebar`, `--accent`, `--ai-running` (live dot), `--bg-secondary`.

## Navigation Rail
- **Purpose:** collapsed icon-only sidebar for narrow widths / focus mode.
- **Anatomy:** `nav` → icon buttons with `aria-label` + `title`; live dot pinned top-right.
- **States/Keyboard/A11y:** as Sidebar Nav; each item keeps its accessible name via `aria-label`.
- **Tokens:** `--width-sidebar-collapsed`, `--nav-item-bg-selected`, `--control-md`.

## Tree View
- **Purpose:** hierarchical browse (decisions by quarter, connectors).
- **Anatomy:** `ul[role=tree]` → `li[role=treeitem]` with `aria-level` / `aria-expanded` / `aria-selected`; a single roving `tabIndex=0`.
- **States:** default · hover · selected (`surface-selected`). Twist glyph indicates expand state.
- **Keyboard:** ↑/↓ move · → expand or dive · ← collapse or out · Enter/Space toggles or selects. Roving tabindex keeps one tab stop.
- **A11y:** flat `treeitem` list with `aria-level` (AT announces depth + expanded). Nest into `role=group` if a production tree needs it.
- **Tokens:** `--nv-indent` (= `--space-20`), `--surface-selected`, `--surface-hover`.

## Breadcrumbs
- **Purpose:** location within the hierarchy.
- **Anatomy:** `nav[aria-label=Breadcrumb]` → `ol`; ancestors are links, the trailing crumb is `span[aria-current=page]`.
- **Keyboard/A11y:** links are tabbable; the current page is non-interactive and announced via `aria-current`.
- **Tokens:** `--text-secondary`/`--text-primary`, `--surface-hover`.

## Tabs
- **Purpose:** switch facets within one resource (Evidence / Debate / Risk / Recommendation).
- **Variants:** **underline** (in-panel sections) · **segmented** (compact toggle).
- **States:** default · hover · selected (underline accent or raised segment + semibold).
- **Keyboard:** roving tabindex — ←/→ move + activate selection, Home/End jump to ends.
- **A11y:** `role=tablist` / `role=tab` / `aria-selected`; only the selected tab is in the tab order.
- **Tokens:** `--accent`, `--surface-raised`, `--elevation-raised`, `--text-button`.

## Command Palette ⭐ (front-loaded signature component)
- **Purpose:** the ⌘K launcher — one keystroke to any resource or action.
- **Anatomy:** floating surface = search head (magnifier + input + ⌘K caps) · grouped result `listbox` · footer with live keyboard hints.
- **States:** typing filters live and re-groups; matched substring is `<mark>`-highlighted; the active row is tinted + accent icon. Empty-query and no-match states handled.
- **Keyboard:** ↑/↓ move selection (wrapping) · Enter runs · Esc clears/dismisses. Input keeps DOM focus throughout.
- **A11y:** input is `role=combobox` with `aria-autocomplete=list` driving `aria-activedescendant` over a `role=listbox`; the highlighted option is announced without moving focus off the field. In product it opens as a centered modal over a dim scrim with the input auto-focused.
- **Tokens:** `--surface-floating`, `--elevation-modal`, `--accent-subtle` (mark + active row), `--nv-palette-w` (= `--width-dialog-md`).

## Quick Switcher
- **Purpose:** scoped, lighter palette — jump between recent runs/decisions/sessions.
- **States:** filtered list with active row; live runs show the amber dot, settled ones a teal check (color + glyph).
- **Keyboard/A11y:** ↑/↓ move; `combobox` + `aria-activedescendant` over `listbox`, same pattern as the palette.
- **Tokens:** `--ai-running` / `--ai-running-text`, `--resolved` / `--text-resolved`, `--nv-switcher-w`.

## Search, filter & order
- **Purpose:** inline search that filters a result set **live as you type**, with composable status filters and a sort control.
- **Anatomy:** search field (leading magnifier + input + clear) · status filter chips (toggle) · sort `select` · live result count · result rows (title + id + status + confidence + date) · empty state.
- **Behavior:** typing filters immediately and highlights the matched substring; status chips toggle (multiple compose, empty = all); sort offers Relevance / Newest / Confidence / A–Z. Filters + sort + query all compose.
- **States:** field default · focus-within · has-value (clear shown); chip default · hover · active (accent border + tinted ground + glyph); empty result set → designed empty message.
- **Keyboard/A11y:** input + clear are labelled; chips are `aria-pressed` toggle buttons; the count is `aria-live="polite"`; status is color **+** glyph **+** label, with the label in the contrast-safe `-text` token (4.5:1 on light). Color is never the only channel.
- **Tokens:** `--field-*`, `--focus-ring-*`, `--surface-selected`/`--accent` (active chip), `--ai-done-text`/`--ai-degraded-text`/`--ai-failed-text`/`--ai-awaiting-human` (status), `--width-dialog-md`.

## Pagination
- **Purpose:** page through long lists (sessions, decisions).
- **Anatomy:** prev arrow · numbered pages with ellipsis windowing · next arrow.
- **States:** current page = tinted + accent border + semibold + `aria-current`; arrows disable at the ends.
- **Keyboard/A11y:** every page/arrow is a labelled `button`; numbers are tabular-figure mono.
- **Tokens:** `--accent-subtle`, `--accent`, `--control-md`, `--state-disabled-*`.

## Stepper
- **Purpose:** linear progress through a multi-stage flow (the pipeline, first-run setup).
- **States:** done (teal check marker + filled connector) · current (accent ring + semibold + `aria-current=step`) · upcoming (muted).
- **Keyboard/A11y:** Back/Next controls are real buttons that disable at the bounds; `aria-current=step` marks position.
- **Tokens:** `--resolved` (done), `--accent` (current), `--btn-*` (controls).

## Context Menu
- **Purpose:** right-click actions on a resource.
- **Anatomy:** `role=menu` surface → grouped `menuitem`s separated by `role=separator`, each with its shortcut; one destructive item set apart.
- **States:** active (hover/keyboard) row tinted; destructive item uses error text + icon and an error-tinted active ground.
- **Keyboard:** opens at the cursor; ↑/↓ move the active item, Enter/Space activates, Esc closes. Menu receives focus on open.
- **A11y:** `role=menu` + `menuitem` + `aria-activedescendant`; the destructive action is distinguished by icon + color + position, not color alone.
- **Tokens:** `--popover-*`, `--z-popover`, `--fb-error-bg`, `--text-error` / `--danger`, `--nv-menu-w`.

### New tokens declared (composed from existing)
`--nv-indent` (`--space-20`), `--nv-palette-w` (`--width-dialog-md`), `--nv-switcher-w` (`--width-dialog-sm`), `--nv-menu-w` (248px — no scale token at that width; flagged).

### Notes / deferrals
- Tree uses a flat `treeitem`+`aria-level` model rather than nested `role=group` (operable; nest if a production tree ships).
- A few preview-framing pixel widths (palette/menu max-widths, context-area min-height) are one-off gallery geometry, not product tokens.
