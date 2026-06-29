# Phase 3D — Data display

The surfaces that make a decision re-readable months later. Token-layer only;
both themes + both densities with zero markup change; every measured value is
mono with `tabular-nums` so it holds its column; status pairs color with a
glyph + label (WCAG 1.4.1). Gallery: "3D · Data display". Source:
`src/phase3/Phase3DataDisplay.tsx` + `phase3d-datadisplay.css` (prefix `dd-`).

---

## Stat / Metric Card (heavy-use)
- **Purpose:** a single headline measurement with trend.
- **Anatomy:** label + sparkline · big mono value · signed delta (arrow glyph **+** sign) + caption.
- **States/tones:** positive (teal/green) · negative (red) · neutral — tone reinforced by the arrow direction and sign, not color alone.
- **A11y:** value is `tabular-nums`; sparkline is decorative (`aria-hidden`), the number carries the meaning.
- **Tokens:** `--text-resolved`/`--success`/`--danger`/`--text-error`, `--accent` (spark), `--surface-default`, `--radius-card`.

## Table
- **Purpose:** rows of decisions/records with sortable, numeric columns.
- **Anatomy:** `table` + `caption` (sr-only) · sticky `thead` with sort `button`s · `tbody` rows; row header is a `th[scope=row]`.
- **States:** header hover · sorted (caret up/down + `aria-sort`) · row hover · selected (`aria-selected` → tinted + inset accent edge) · row focus.
- **Keyboard:** sort headers are buttons (Enter/Space); rows are focusable and Enter/Space-selectable.
- **A11y:** `scope` on every header, `aria-sort` reflects the active column, numeric columns right-aligned + mono.
- **Tokens:** `--table-*`, `--accent`, `--ai-confidence-*` (inline confidence), `--radius-card`.

## Data Grid
- **Purpose:** denser table for synced records at scale.
- **Anatomy:** as Table, compacter rows + a column-resize affordance (`col-resize` cursor) on each header edge.
- **Tokens:** `--dd-resize-w` (= `--space-6`), `--cursor-col-resize`, `--table-*`.

## List
- **Purpose:** single- or multi-line rows (sessions, pipeline steps).
- **Anatomy:** leading icon · text (title + optional sub) · trailing meta (mono value + status badge).
- **States:** hover · focus; rows are focusable.
- **Tokens:** `--row-height`, `--pad-cell-x`, `--surface-hover`.

## Tree
- **Purpose:** nested resources (workspace → decisions/connectors → files).
- **Anatomy:** `ul[role=tree]` → `li[role=treeitem]` with `aria-expanded`/`aria-level`; per-level indent via `--dd-tree-level`.
- **Keyboard:** rows focusable; Enter/Space toggle.
- **Tokens:** `--dd-tree-indent` (= `--space-20`), `--surface-hover`.

## Property / Description List & Key/Value Viewer
- **Purpose:** decision metadata (`dl`) and compact run parameters (key→value rows).
- **Anatomy:** `dl` grid of `dt`/`dd`; key/value viewer is a bordered two-column grid, numeric values tinted as links.
- **A11y:** real `dl`/`dt`/`dd` semantics; values are mono.
- **Tokens:** `--bg-secondary` (key cell), `--text-link` (numeric value), `--radius-card`.

## Badge / Tag / Chip / Avatar
- **Badge:** status pill = fill color **+** glyph (or live pulse) **+** label. Live = amber pulse (reduced-motion parks it). Statuses ground in the real node states (done/running/waiting/degraded/failed/awaiting-human/cancelled).
- **Tag:** category label; `--accent` variant for emphasized tags; sentiment tags carry a direction glyph + border color.
- **Chip:** removable filter token with a labelled close button.
- **Avatar:** image · initials · fallback user glyph; sizes sm/md/lg; fill tinted per analyst.
- **Tokens:** `--ai-*` status, `--accent-subtle`, `--avatar-{sm,md,lg}`, `--radius-pill`.

## Code Block & JSON Viewer
- **Code Block:** mono source, line-number gutter, copy button with a copied-confirmation (`aria-live`).
- **JSON Viewer:** collapsible tree tinted via semantic text roles (key = link, string = resolved, number = warning, bool = info) — **not** a rainbow; toggles are real buttons with `aria-expanded`.
- **Tokens:** `--text-code`, `--surface-sunken`, `--dd-json-indent` (= `--space-16`), `--text-link`/`--text-resolved`/`--text-warning`/`--text-info`.

## Timeline & Activity Feed
- **Timeline:** vertical run timeline — node marker (status fill + glyph, live = pulse) on a rail + body (node, badge, note) + right-aligned time/duration (mono).
- **Activity Feed:** avatar/icon · actor + action + target · timestamp.
- **Tokens:** `--timeline-rail`, `--dd-marker` (= `--icon-md`), `--dd-rail-w` (= `--border-width-strong`), `--ai-*`.

## Diff Viewer
- **Purpose:** prompt-registry version change.
- **Anatomy:** unified rows with old/new line numbers · a +/− sign column · text; additions/removals carry **both** a sign and a tint (never color alone).
- **A11y:** `role=table`/`row`/`cell`; the sign is the non-color channel.
- **Tokens:** `--fb-success-bg`/`--fb-success-text` (add), `--fb-error-bg`/`--fb-error-text` (del), `--text-code`.

## Markdown Renderer
- **Purpose:** rendered recommendation / long-form prose.
- **Anatomy:** styled h2/h3/p/strong/ul/li/code/a/blockquote at prose measure (`--measure-prose`).
- **Tokens:** `--text-heading-3`/`--text-heading-4`/`--text-body-m`, `--text-link`, `--accent` (blockquote rule).

### New tokens declared (composed from existing)
`--dd-rail-w` (`--border-width-strong`), `--dd-marker` (`--icon-md`), `--dd-resize-w` (`--space-6`), `--dd-json-indent` (`--space-16`), `--dd-tree-indent` (`--space-20`).

### Notes
- Sample avatar portrait is an inline data-URI (demo content, no network) — not a token.
- A few preview-framing widths (confidence track 56px, prop-conf max-width) are gallery geometry, not product tokens. The full color/spacing/radius/type/elevation scale is strictly token-only (verified: no raw color literals).
