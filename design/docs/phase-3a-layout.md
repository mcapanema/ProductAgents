# Phase 3A — Layout

The structural frame of the ProductAgents desktop GUI: the app shell, its
regions, multi-pane panels, the layout primitives, the card, and scroll areas.
Everything here is built from the token layer only (semantic + component +
theme), so every piece adapts across both themes and both densities with zero
markup change. Live gallery: `styleguide` → 3A · Layout.

Icons are inline Phosphor-style SVG (`viewBox 0 0 24 24`, `stroke currentColor`,
`stroke-width 1.75`, round caps). `fill` weight is used only for the single
active/selected nav item.

---

## App Shell

- **Purpose** — the resource-explorer composition root: window frame + resource
  sidebar + top bar + context toolbar + main + inspector. The frame every
  resource view renders inside.
- **When to use / not** — the single top-level layout of the desktop window. Not
  a reusable widget; there is exactly one per window.
- **Anatomy** — `la-shell` (2-row grid: title bar / body) → `la-shell-body`
  (3-column grid: rail / main / inspector). `la-main` is itself a 3-row grid
  (top bar / context toolbar / scrolling content).
- **Variants** — with or without the inspector column; rail expanded or collapsed.
- **States** — inherits the states of its child regions.
- **Keyboard** — every interactive child (nav items, tabs, window controls,
  resize handle, search) is focusable with a visible focus ring.
- **Accessibility** — landmark elements: `nav[aria-label]` rail, `main`,
  `aside[aria-label]` inspector, `header` title bar.
- **Tokens** — `--width-sidebar`, `--width-inspector`, `--control-md/-lg`,
  `--bg-primary/-secondary/-tertiary`, `--border-subtle`, `--radius-card`,
  `--elevation-raised`. New: `--la-rail-w`, `--la-inspector-w`,
  `--la-titlebar-h`, `--la-topbar-h`, `--la-toolbar-h`, `--la-shell-h`.

## Window Frame (title bar)

- **Purpose** — the OS chrome region (Tauri-drawn) carrying the app identity and
  window controls.
- **When to use / not** — top edge of the shell only.
- **Anatomy** — `la-titlebar`: title + sub + spacer + `la-win-controls`
  (minimize / maximize / close icon buttons).
- **States** — control hover (close goes `--danger`); `:focus-visible` ring.
- **Keyboard** — each window control is a real `button` with an `aria-label`.
- **Accessibility** — `header` landmark; controls grouped with `aria-label`.
- **Tokens** — `--bg-tertiary`, `--text-title/-caption`, `--control-sm`,
  `--danger`/`--on-signal`, `--surface-hover`. New: `--la-titlebar-h`.

## Navigation Sidebar (resource list)

- **Purpose** — the resource explorer: Run, Workflows, Sessions, Decisions,
  Connectors, Prompts, Settings.
- **When to use / not** — primary navigation between resources. Not for in-page
  tab switching (use the context toolbar tabs).
- **Anatomy** — `la-rail` → `la-rail-head` + `la-nav` list of `la-nav-item`
  (accent `la-nav-marker` edge + icon + label).
- **Variants** — expanded (`--la-rail-w`) and collapsed icon rail
  (`la-rail--collapsed`, `--width-sidebar-collapsed`); `la-rail--secondary` for a
  scoped second list.
- **States** — hover, active/selected (`aria-current="page"`, filled icon, accent
  marker + tinted ground), focus ring (inset).
- **Keyboard** — items are anchors in a list; Tab order top-to-bottom.
- **Accessibility** — active item carries `aria-current="page"` so selection is
  not color-only; marker adds position, filled icon adds shape.
- **Tokens** — `--nav-item-*`, `--row-height`, `--surface-selected`,
  `--accent`/`--accent-text`, `--text-secondary/-primary/-tertiary`.

## Top Bar

- **Purpose** — contextual breadcrumb + global search + the primary action for
  the current resource.
- **Anatomy** — `la-topbar`: `la-crumbs` · spacer · `la-search` (field + `⌘K`
  kbd) · primary button.
- **States** — search `:focus-within` ring; breadcrumb link hover/focus.
- **Keyboard** — breadcrumb links, search input, and action button focusable.
- **Accessibility** — `nav[aria-label="Breadcrumb"]`, `role="search"`, current
  crumb `aria-current="page"`.
- **Tokens** — `--field-*`, `--bg-primary`, `--border-subtle`, `--font-mono`.
  New: `--la-topbar-h`.

## Context Toolbar

- **Purpose** — view tabs scoped to the selected resource + a live status pill.
- **Anatomy** — `la-toolbar`: `la-tabs` (`role="tablist"`) · spacer ·
  `la-runpill` (amber dot + animated ping + label).
- **States** — tab hover/active (accent underbar), live pill animates (parked
  under `prefers-reduced-motion`).
- **Keyboard** — tabs are buttons with `role="tab"` + `aria-selected`.
- **Accessibility** — live state is amber **and** an animated dot **and** the
  text "Running" (never color alone, WCAG 1.4.1).
- **Tokens** — `--ai-running`/`--ai-running-text`, `--accent`, `--text-button`,
  `--dur-slower`. New: `--la-toolbar-h`.

## Secondary Sidebar

- **Purpose** — a scoped second navigation list (e.g. recent sessions) beside the
  primary rail.
- **Anatomy** — `la-rail la-rail--secondary` with the same nav primitives.
- **Tokens** — `--bg-tertiary` + the nav tokens above.

## Inspector Panel

- **Purpose** — right-hand detail for the selected resource (key/value metadata).
- **When to use / not** — supplementary detail; the main column stays the focus.
  Collapsible when space is tight.
- **Anatomy** — `la-inspector`: head + `la-kv` definition list of `la-kv-row`
  (`dt` label / `dd` mono value).
- **Accessibility** — `aside[aria-label="Inspector"]`; semantic `dl/dt/dd`.
- **Tokens** — `--width-inspector`, `--bg-secondary`, `--text-secondary`,
  `--font-mono` (tabular). New: `--la-inspector-w`.

## Split / Resizable / Docked Panels

- **Purpose** — multi-pane working areas with adjustable proportions.
- **Anatomy** — `la-split` (panes + `la-resize` handle), `la-dock` (main +
  bottom-docked tabbed panel).
- **Variants** — side-by-side split with a vertical resize handle; bottom-docked
  panel with tabs (Logs / Problems).
- **States** — resize handle hover (grip turns accent) + `col-resize` cursor;
  focus ring; dock tab hover/active.
- **Keyboard** — the resize handle is `role="separator"` `aria-orientation`
  `tabIndex={0}` and focusable; dock tabs are `role="tab"` buttons.
- **Accessibility** — separator has an `aria-label`; panes keep a `--width-panel-min`
  floor.
- **Tokens** — `--width-panel-min`, `--cursor-col-resize`, `--border-strong`,
  `--accent`, `--surface-sunken/-default`. New: `--la-resize-w`.

## Workspace · Page Container · Section primitive

- **Purpose** — the nesting hierarchy inside a resource view: workspace canvas →
  width-capped page → titled section.
- **Anatomy** — `la-workspace` (canvas) → `la-page` (max-width `--width-content-max`,
  page padding, centered) → `la-prim-section` (title + desc).
- **Tokens** — `--width-content-max`, `--pad-page`, `--pad-card`,
  `--text-heading-4`, `--gap-stack`.

## Surface

- **Purpose** — the interactive material tiers components sit on.
- **Variants** — default / raised (resting shadow) / sunken (wells, inputs, logs).
- **Tokens** — `--surface-default/-raised/-sunken`, `--elevation-raised`,
  `--border-subtle`, `--radius-card`.

## Divider

- **Purpose** — separate content groups.
- **Variants** — horizontal `hr.la-divider`; vertical
  `la-divider--v` (`role="separator"` `aria-orientation="vertical"`).
- **Accessibility** — semantic `hr` / `role="separator"`.
- **Tokens** — `--border-subtle`, `--border-width-default`, `--icon-size-md`.

## Card

- **Purpose** — the default content container.
- **When to use / not** — group related content. **Never nest cards** (anti-slop);
  use sections/surfaces inside instead.
- **Anatomy** — `la-card` → optional `la-card-head` (title + meta, bottom divider)
  + `la-card-body`.
- **Variants** — default (subtle border, no shadow) vs raised (`la-card--raised`,
  raised surface + resting shadow); with / without header.
- **Tokens** — `--card-bg`/`--card-bg-raised`, `--card-border`, `--card-radius`,
  `--card-pad`, `--card-shadow`.

## Scroll Area

- **Purpose** — an overflow region with a styled, unobtrusive scrollbar.
- **Anatomy** — `la-scroll` (thin track, pill thumb via `scrollbar-*` +
  `::-webkit-scrollbar*`).
- **States** — thumb hover darkens to `--border-strong`.
- **Accessibility** — keyboard-scrollable; thumb sized for pointer use.
- **Tokens** — `--border-default/-strong`, `--radius-pill`, `--surface-sunken`,
  `--text-terminal`. New: `--la-scroll-h`.

---

## New tokens declared (3A)

All composed from existing tokens (see top of `phase3a-layout.css`):

| Token | Composition | Purpose |
| --- | --- | --- |
| `--la-rail-w` | `var(--width-sidebar)` | resource rail width |
| `--la-rail-collapsed-w` | `var(--width-sidebar-collapsed)` | collapsed icon rail |
| `--la-inspector-w` | `var(--width-inspector)` | inspector column width |
| `--la-titlebar-h` | `var(--control-md)` | window title bar height |
| `--la-topbar-h` | `var(--control-lg)` | top bar height |
| `--la-toolbar-h` | `var(--control-md)` | context toolbar height |
| `--la-resize-w` | `var(--space-12)` | resize-handle hit area |

`--la-shell-h`, `--la-region-h`, `--la-scroll-h` are one-off **demo viewport
heights** for the contained gallery preview boxes only — not product geometry.
