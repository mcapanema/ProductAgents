# Ant Design Styleguide Pilot — Evaluation

**Date:** 2026-07-01
**Scope:** `design/styleguide/src/antd-pilot/` — Buttons, Forms (Input/Select/Checkbox/Radio/Switch),
Table, Overlays (Modal/Drawer/Tooltip/Popover), Navigation (Menu/Tabs/Breadcrumb), themed via
`ConfigProvider` from the existing `design/tokens/*.css` "Instrument" tokens.

## Coverage vs. the hand-built system

| Area | Phase 3 module | AntD Pilot module | Notes |
|---|---|---|---|
| Buttons & forms | `Phase3Forms.tsx` (3C) | `AntdPilotForms.tsx` | Roughly at parity for the piloted controls. Phase 3C uses hand-rolled icons (`IcoCalendar`, `IcoEye`/`IcoEyeOff`, etc.) for affordances like password-reveal and date pickers that the pilot didn't attempt to replicate — AntD ships equivalents (`Input.Password`, `DatePicker`) but they weren't exercised here. AntD's `Form` gives declarative `rules`-based validation for free (tested live: submitting empty shows "Workspace name is required" inline, no hand-written validation logic needed). |
| Table | `Phase3DataDisplay.tsx` (3D) | `AntdPilotDataDisplay.tsx` | Large gap. Phase 3D covers a much broader data-display surface — `DataGrid`, `Sparkline`, `ConfidenceBar`/`ConfidenceMini`, `Avatar`, `MetricCard`, `Badge`, a JSON tree view (`JsonNode`/`JsonLeaf`/`TreeNode`). The pilot only covers `Table` (sortable + filterable), which AntD handles well out of the box, but the pilot doesn't demonstrate whether AntD's `Table` scales to the denser, more custom-rendered rows Phase 3D shows (sparklines/confidence bars inside cells) — that would need custom `render` functions, unverified here. |
| Overlays | `Phase3Overlays.tsx` (3F) | `AntdPilotOverlays.tsx` | Close parity for Modal/Drawer/Tooltip/Popover. Phase 3F also has a `CommandSurface`/`CommandDemo` (command palette) that the pilot didn't attempt — AntD has no built-in command-palette component; would need a third-party addition (e.g. `cmdk`) if adopted. |
| Navigation | `Phase3Navigation.tsx` (3B) | `AntdPilotNavigation.tsx` | Phase 3B is substantially richer: `CommandPalette`, `ContextMenu`, `NavRail`, `Pagination`, `QuickSwitcher`, `SearchBar`/`SearchExplorer`, `Stepper`, `TreeView`, in addition to `Breadcrumbs`/`Tabs`. The pilot only covers Menu/Tabs/Breadcrumb. AntD does ship `Pagination`, `Steps` (a `Stepper` equivalent), and `Tree` (a `TreeView` equivalent) that weren't piloted but exist in the library if a fuller port were attempted; it has no built-in command palette or quick-switcher.

Not piloted (out of scope for this plan): layout (3A), data-display beyond Table, feedback/toasts (3E),
all of Phase 4–10 (AI components, workflow/CLI, project, settings, monitoring, empty states, patterns).

## Theming fidelity

- `contrast.py`: **PASS — `TOTAL FAILURES: 0`** (identical to the pre-pilot baseline; the pilot introduces no new colors, only reads existing tokens).
- Visual match to "Instrument" (indigo primary, light default, dark required): in steady state, the match is good — `buildAntdTheme` correctly seeds `colorPrimary`/`colorError`/`colorSuccess`/etc. from the real token values, so buttons, tags, and form controls read as the same indigo/amber/teal/red palette as the rest of the styleguide, not AntD's default blue. Verified live in the browser for both themes.
- **Real bug found:** the *first* click that switches `theme` from light→dark (or vice versa) renders with **stale colors for one commit** — Input/Select backgrounds and several body/label texts render using the *previous* theme's resolved CSS custom-property values (e.g. a white Input box and near-invisible label text on the newly-dark page), while Button colors (computed via AntD's `algorithm`, not read as a literal) look correct immediately. A second, unrelated re-render (e.g. toggling Density) self-corrects it. Root cause: `buildAntdTheme()` calls `getComputedStyle(document.documentElement)` synchronously during React's render phase, but `App.tsx`'s `useLayoutEffect` that writes the new `data-theme` attribute onto `<html>` hasn't committed yet at that point — so the theme-adapter call and the DOM attribute write race, and the adapter loses on the very click that changes the theme. This directly contradicts the assumption written into `sg.tsx`'s `useResolvedVars` JSDoc (which this plan's `theme.ts` doesn't use, calling `getComputedStyle` directly instead) and is worth fixing (e.g. read the resolved vars in a `useLayoutEffect`/`useMemo` keyed off a value that only changes after the attribute commit) before this pattern is reused anywhere theming reacts to live toggles.
- Density: AntD's `compactAlgorithm` visibly tightens control heights and vertical rhythm in both themes (confirmed in the browser) — comparable in feel to the hand-built comfortable/compact toggle, though no pixel-level comparison was done.

## Accessibility

- Keyboard: `Escape` closes both the `Modal` and the `Drawer`, and in both cases focus visibly returns to the triggering button (confirmed with a visible focus ring in the browser). Table sort headers and filter dropdowns are keyboard/click accessible. Menu items respond to `Arrow Down` by moving visible keyboard focus between items; a single follow-up check of `Enter`-to-select did not visibly update the selected/highlighted item in that one test — this needs a more thorough follow-up pass before relying on it, noted here rather than asserted as broken or working.
- Focus visibility: clear, visible focus rings observed on buttons after Modal/Drawer close, and on Table's sort/filter controls.
- No console errors or warnings were produced by any interaction tested (page load, theme/density toggles, Modal/Drawer/Tooltip/Popover open-close, Table sort/filter, Menu/Tabs clicks) — including during the dark-mode color-lag bug above, which is a silent visual bug, not one that surfaces in the console.

## Cost

- `antd` installed size: **58M** (`node_modules/antd`)
- `@ant-design/icons` installed size: **46M** (`node_modules/@ant-design`)
- Built JS bundle size: pre-pilot baseline (Task 1, before any antd-consuming code) was **542.40 kB** (**149.53 kB gzip**); after all four gallery modules (Task 7) it is **1,319.18 kB** (**398.46 kB gzip**) — a delta of roughly **+777 kB raw / +249 kB gzip** for antd + `@ant-design/icons` + the four pilot modules combined. Vite's build warns this chunk now exceeds its 500 kB advisory limit.
- New dev dependency: `vitest` + `jsdom` (this package had no test runner before this pilot).

## Verdict

**Hybrid, not a full replacement.** AntD delivers broad, correct-looking, and genuinely accessible behavior (validated Forms, sortable/filterable Table, Modal/Drawer with correct focus return, Menu/Tabs/Breadcrumb) for a fraction of the hand-written code the equivalent Phase 3 modules required — and the theme adapter proves the existing "Instrument" tokens *can* drive AntD's `ConfigProvider` convincingly in steady state. But two findings hold back a wholesale migration of `desktop/src/ui/`:

1. The dark-mode color-lag bug is a real correctness issue in exactly the "read CSS custom properties synchronously during render" pattern this plan used, and would need a fix (documented above) before any production use of a live-toggling `ConfigProvider`.
2. The bundle-size cost (+249 kB gzip for `antd` core plus four modules, on top of an already-existing hand-built system) is non-trivial, and the coverage gap analysis above shows the hand-built system already goes well beyond AntD's stock components in several areas (JSON tree views, sparklines, confidence bars, command palette, quick-switcher) that `desktop/src/ui/` likely also needs — those would still require custom components either way.

Recommendation: **do not replace the hand-built system wholesale.** Consider AntD selectively for genuinely data-heavy widgets where its built-in behavior (sortable/filterable `Table`, validated `Form`) offers the most leverage over hand-rolled equivalents, while keeping the existing system for the custom/product-specific surfaces (data-display widgets, navigation patterns) it already covers that AntD doesn't ship out of the box.
