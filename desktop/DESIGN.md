# Design

> **Pointer file.** The canonical, living design system is
> [`../design/DESIGN.md`](../design/DESIGN.md) (with the phased
> component/pattern detail under [`../design/docs/`](../design/docs/)). This file is a summary so
> impeccable commands run from `desktop/` can find the visual system; **edit the source in
> `design/`, not here.**

## Direction — "Instrument"

A precision, telemetry-grade panel in the lineage of LangSmith, Datadog, and GitHub Actions —
warmer and hand-built, not a generic ops dashboard. A decision is treated as **measured
quantities**; the signature motif is **confidence as a calibration gauge** on every verdict, and
a **span/reasoning timeline** is the Run centerpiece. Calm, exacting, defensible. Deliberately
avoids cornflower-blue-on-near-black SaaS slop and the dark-plus-neon-green AI-tool cliché.

## Color

OKLCH-derived, committed brand identity — **do not reseed**. Two restrained signal hues do the
semantic work against a near-neutral ground, across both themes:

| Role | Token | Dark | Light | Intent |
| --- | --- | --- | --- | --- |
| **Primary** | `--primary` (indigo) | `#6267CA` | `#565CAE` | interactive accent — buttons / links / focus / selected |
| **Signal** | `--signal` (amber) | `#E0A33E` | — | live / running / needs-attention (status, not interaction) |
| **Resolved** | `--resolved` (teal) | `#3FB5A6` | — | measured / settled / done |
| Canvas | `--bg` (cool slate / warm sand) | `#14171C` | warm off-white | quiet ground; **never** `#000` |

Feedback (red/green/blue) and the five CVD-distinct **analyst** hues are defined in the token
layer. Every signal pairs with a glyph/label/position — color is never the only channel (WCAG 1.4.1).

## Typography

- **IBM Plex Sans** — UI / body (display role = Plex Sans at large weights).
- **IBM Plex Mono** — data, traces, spans, numbers (tabular figures for measured values).
- Shipped locally from `public/fonts/` (SIL OFL, no runtime web-font fetch). 1.20 minor-third scale.

## Tokens (source of truth)

Layered CSS custom properties, cascading:
`../design/tokens/primitives.css` → `semantic.css` + `themes/{dark,light}.css` → `components.css`.
The desktop app consumes them via `src/ui/tokens.css` (which re-exports the layered source plus
`fonts.css`). `src/ui/theme.ts` maps these onto AntD's `ConfigProvider` seed tokens; `ThemeShell`
writes `data-theme` / `data-density` onto `<html>`.

## Themes & density

Dark is primary (dim rooms, long sessions); light is fully designed (bright offices, board decks).
A theme redefines **only** color roles — components wired to semantic tokens change zero code across
themes. `[data-density]` (comfortable / compact) rescales spacing roles only, never type.

## Verification gate

Contrast is **computed, never asserted**: `python3 design/contrast.py` must report
`TOTAL FAILURES: 0` (both themes, incl. protanopia/deuteranopia) on every palette change.
