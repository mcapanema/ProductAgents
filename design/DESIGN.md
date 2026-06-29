# ProductAgents Design System

> Living reference. Built phase by phase (see [`design-system-plan.md`](./design-system-plan.md));
> the durable brief is [`design-system-context.md`](./design-system-context.md). The v0 attempt is
> archived in [`_v0/`](./_v0/) as reference, not spec.

---

## Direction — "Instrument" *(signed off, Phase 0, 2026-06-29)*

ProductAgents is a precision instrument for reasoning under uncertainty, so it should look like one:
a telemetry-grade panel in the lineage of LangSmith, Datadog, and GitHub Actions — but warmer and
hand-built, not a generic ops dashboard. The interface treats a decision as **measured quantities**:
five specialists analyze, an advocate and skeptic argue, a strategist proposes, a judge scores, and
every verdict carries a visible **confidence reading**. The signature element is *confidence as a
measured quantity* — one calibration-gauge motif that recurs on every verdict — and a **span timeline**
as the Run centerpiece (replacing today's raw `JSON.stringify` dump). The register is calm, exacting,
and defensible; it deliberately avoids both AI-tool slop reflexes (cornflower-blue-on-near-black and
the dark-plus-neon-green developer cliché).

### Palette intent
Two restrained signal hues do the semantic work against a near-neutral ground:

| Role | Dark variant | Intent |
| --- | --- | --- |
| Canvas | `#14171C` cool graphite (never `#000`) | quiet, low-emission ground for long sessions |
| Panel / raised surface | `#1B1F26` | machined-panel separation |
| Text / muted | `#E2E6EC` / `#8A93A0` | high legibility at density |
| **Primary (indigo)** | `#6267CA` | the interactive accent — buttons / links / focus / selected |
| **Signal (amber)** | `#E0A33E` | live / running / needs-attention (status, not interaction) |
| **Resolved (teal)** | `#3FB5A6` | measured / settled / done |

Light variant ground is a warm-neutral off-white (defined in Phase 1). Signal hues carry across both
themes. Every signal pairs with glyph/label/position — color is never the only channel (WCAG 1.4.1).

> **Phase 1 refinement (owner, 2026-06-29):** the **interactive primary is indigo**, not amber. Amber
> reads as a bright gold that only holds up on the dark canvas — darkened for the light theme it collapses
> to muddy brown, so its identity isn't stable across themes. Indigo holds its hue at both light and dark
> lightness, takes a white label on its fill in both themes, and sits clear of the cornflower-blue slop
> reflex. **Amber is retained as the live/running status signal** (its natural job), where it shines.
*The five analyst perspectives still need a CVD-distinct, system-wide palette (a strong idea borrowed
from the "Editor" candidate) — to be defined as part of the Phase 2F AI tokens.*

### Type intent
- **IBM Plex Sans** — UI / body (OSS, SIL OFL, ships locally; precise-instrument character).
- **IBM Plex Mono** — data, traces, spans, numbers (tabular figures for measured values).
- Display role = Plex Sans at large weights initially; revisited in Phase 2B.

Final faces are confirmed in Phase 1 (primitives) / Phase 2B (type styles) and dropped into
`styleguide/public/fonts/`.

---

## Phase 0 decisions *(2026-06-29)*

- **Default theme: LIGHT** — owner override of the brief's dark-first default. Dark remains a required,
  fully-designed theme; light is primary/default. Never pure `#000` in dark. High-contrast theme: later.
- **Review surface:** the browser styleguide is the *sole* review surface. The Pencil `.pen` mirror is
  dropped (its screenshots are unreliable here — context §7).
- **v0 artifacts archived** to [`_v0/`](./_v0/) (`DESIGN.md`, `design-system.pen`,
  `design-system-phases.md`). `contrast.py` kept and reused as the CI gate.

### Artifact homes (confirmed)
- **Tokens (source of truth):** `design/tokens/*.css` — `primitives.css` → `semantic.css` →
  `components.css` → `themes/{light,dark}.css`.
- **Styleguide (review surface):** `design/styleguide/` — standalone Vite + React + TS app
  (`npm run dev`, port 5174). Theme + density toggles driven by `data-theme` / `data-density` on
  `<html>`. Local OSS fonts via `src/fonts.css` + `public/fonts/` (no runtime web-font fetch).
- **Components:** `design/styleguide/components/<Component>/` during design; migrate to
  `desktop/src/ui/` when adopted into the app (a later, separate step).
- **Contrast gate:** `design/contrast.py` (extend `PAIRS` on every palette change; CI gates on
  `TOTAL FAILURES: 0`).
- **Living doc:** this file, rewritten incrementally per phase (Phase 11 template).

---

## Phase 1 — Foundation primitives *(2026-06-29)*

The raw, theme-agnostic values everything derives from, as CSS custom
properties in [`tokens/primitives.css`](./tokens/primitives.css). Not semantic:
components never reference a primitive directly — Phase 2 maps them into roles,
and [`tokens/themes/{dark,light}.css`](./tokens/themes/) redefine only the
*roles*. Rendered in the **Foundations gallery** (`styleguide/`, both themes +
densities). The OKLCH ramp generator and the contrast probe that produced these
hexes are reproducible; the gate is [`contrast.py`](./contrast.py).

### Color ramps
Seven OKLCH-derived ramps, hexes pinned, gated by `contrast.py` (**0 failures**,
both themes, incl. protanopia/deuteranopia). Two neutrals carry the Instrument
cool-dark / warm-light temperature split; five chromatic signal ramps. Step 500
is the saturated anchor (the signatures `amber-500 #E0A33E`, `teal-500 #3FB5A6`
are pinned exactly); lighter steps carry text on dark grounds, darker steps on
light grounds.

| Ramp | Role | Steps |
| --- | --- | --- |
| `--c-slate-*` | cool graphite — dark grounds + cross-theme ink/border | 50–950 (incl. 450/850) |
| `--c-sand-*` | warm neutral — light grounds | 50–950 (incl. 450/850) |
| `--c-indigo-*` | **primary** — interactive accent (buttons / links / focus / selected) | 50–950 |
| `--c-amber-*` | **signal** — live / running / attention | 50–950 |
| `--c-teal-*` | **resolved** — measured / settled / done | 50–950 |
| `--c-red-*` · `--c-green-*` · `--c-blue-*` | danger · success · info | 50–950 |

`indigo-500 #6267CA` (dark fill) / `indigo-600 #565CAE` (light fill) are pinned from the owner-approved
candidate; `--primary` + `--on-primary` (white) + `--primary-text` and the `--focus` ring all derive from
this ramp. Interactive affordances use the primary; amber/teal/red/green/blue are reserved for state.

Every signal pairs with a glyph/label (color is never the only channel, WCAG
1.4.1) — warm-vs-warm and teal-vs-blue pairs are *not* luminance-distinguished
under CVD, so glyph + position are load-bearing (see `contrast.py` notes).

### Other primitives (all in `primitives.css`)
- **Type:** IBM Plex Sans (UI/body) + IBM Plex Mono (data/traces), shipped
  locally in `styleguide/public/fonts/` (SIL OFL, no runtime fetch). 1.20
  minor-third size scale (`--fs-xs…5xl`), weights 400–700, four line-heights,
  three letter-spacings. Display role = Plex Sans for now (revisit Phase 2B).
- **Space:** 4px grid (`--space-2…96`). **Radius:** `none…full` (restrained).
  **Border:** hairline/thin/medium/thick. **Elevation:** `--shadow-xs…xl`
  (dark-canvas-tuned). **Opacity, blur, z-index, breakpoints, motion**
  (durations + four easings + presets), **sizes** (icon/avatar/control/field).

### Theme scaffold
`themes/{dark,light}.css` map primitives onto the core surface/text/border/
primary/signal **roles** (`--bg --panel --elevated --well --field --hairline
--structural --focus --ink --muted --on-primary --on-signal --primary --signal
--resolved --danger --success --info` + `*-text`). This is the *mechanism* —
Phase 2A expands it to the full semantic set. Dark = cool slate grounds (never
`#000`); light = warm sand grounds; `--primary`/`--focus` come from indigo
(500/400 dark · 600/700 light); signal *text* uses the 300 step on dark / 700 on
light; `on-signal` is a dark ink for the 500 fills, `on-primary` is white.

**Definition of Done — met:** Foundations gallery renders in both themes (browser
verified); `contrast.py` → `TOTAL FAILURES: 0`; scales on-grid; no off-scale
literals; ramps monotonic.

---

*Subsequent phases append their foundations, tokens, and component docs below as they land.*
