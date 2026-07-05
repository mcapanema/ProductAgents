# ProductAgents Design System

> Living reference. Built phase by phase (see [`design-system-plan.md`](./design-system-plan.md)).
> This file carries the direction and the
> Phase 0–2 token foundations in full, then indexes the Phase 3–10 component/pattern detail, which
> lives in [`design/docs/`](./docs/) (one file per phase or sub-phase) — see the *Component &
> pattern reference* section below.

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
- **v0 artifacts discarded** (`DESIGN.md`, `design-system.pen`,
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

## Phase 2 — Token architecture *(2026-06-29)*

The layered semantic system components actually consume, built on Phase-1
primitives. Three new files complete the cascade:

```
primitives.css                    raw, theme-agnostic values (Phase 1)
        ↓
semantic.css  +  themes/{dark,light}.css     the semantic layer (split, see below)
        ↓
components.css                    per-component token sets + the state matrix
        ↓
component implementations         (Phase 3+)
```

**Architecture decision — where color lives.** The semantic layer is split by
*what changes between themes*:
- **`themes/{dark,light}.css` own every COLOR semantic token** — backgrounds,
  surfaces (+ states), the text ladder, borders, the accent system, signals,
  feedback sets, and the AI tokens. A theme redefines *only* these, so a
  component wired to them changes **zero** code across light/dark (the 2H
  contract). This is why the plan's "2A → semantic.css" suggestion resolves into
  the theme files: color is theme-dependent by definition.
- **`semantic.css` owns every NON-color semantic token** — composed type styles,
  dimensional roles, layout/interaction/focus roles, the density system, and the
  non-color a11y tokens — shared verbatim by both themes.
- **`components.css`** composes both into per-component handles (`--btn-*`,
  `--field-*`, `--chip-*`, `--timeline-*`, `--gauge-*`, …) plus a reusable state
  matrix. It is theme-agnostic; state derivations without a dedicated token use
  `color-mix(in oklab, …)` over a theme token, never a literal.

### Sub-phases
- **2A — Color semantic.** Background (primary/secondary/tertiary/elevated/overlay/
  inverse), Surface (default/raised/floating/sunken/hover/pressed/selected), the
  Text ladder (primary/secondary AA · tertiary at the 3:1 UI floor · disabled
  exempt · link · on-accent · per-signal), Border (subtle/default/strong/focus/
  per-signal), and four Feedback sets (success/warning/error/info × bg·surface·
  border·text·icon). Feedback borders are theme-asymmetric — **500** on the dark
  canvas, **600** on the light canvas — so the boundary clears 3:1 either way.
- **2B — Type styles.** 14 composed `font`-shorthand styles (Display, Heading 1–4,
  Title, Body L/M/S, Caption, Label, Button, Code, Terminal) + a `-tracking`
  companion each. Code/Terminal are mono with tabular figures.
- **2C — Dimensional.** Radius (by surface kind), border-width, elevation
  (raised→modal, light re-tints the shadows softer), motion presets, blur, sizes.
- **2D — Layout / interaction / iconography.** Container & panel widths, the
  **density system** (`[data-density]` rescales spacing roles only — never type),
  focus ring (offset is load-bearing), cursors, semantic z-index, and the locked
  **icon set: Phosphor (MIT), regular weight, fill reserved for the active item**,
  SVG only.
- **2E — Component + state.** Button (primary/secondary/ghost/danger), field,
  card/panel, chip, nav, table, tooltip/popover, overlay/dialog, alert/toast, and
  the AI execution-timeline / log / confidence-gauge geometry — plus the 11-state
  matrix (hover/pressed/selected/disabled/loading/dragging/invalid/…).
- **2F — AI-specific.** Grounded in the real event vocabulary (`ProgressEvent`,
  `NodeComplete`, `DebateTurn`, `Judgment`, `ApprovalRequested`, `FinalVerdict`,
  `RunAborted`; node states waiting/running/done/degraded/failed/awaiting-human).
  amber = **live** (its reserved job), teal = **settled**, indigo = **your turn**,
  red = failed, slate = inert. Plus log levels (trace→critical), the
  confidence-gauge scale (the signature motif — color reinforces a shown numeric
  reading), the advocate/skeptic dialectic, and the **five analyst perspectives**.
  *CVD-honest:* the analyst hues are **not** all separable under protan/deutan, so
  each analyst also carries a unique shape **and** a label **and** a fixed
  position — color is the weakest of the three channels (see `contrast.py` notes).
- **2G — Accessibility.** Min-contrast/target tokens, focus colors (per theme),
  a global **reduced-motion** switch (collapses the primitive durations, which the
  motion presets re-resolve — instant transitions system-wide with no per-component
  edit), and a `prefers-contrast: more` hook (thicker borders + ring; the full
  high-contrast *theme* remains a later phase).
- **2H — Theme mapping.** Both themes redefine only the color roles; verified by
  `contrast.py`.

**Definition of Done — met:** the token-reference gallery (organized by sub-phase)
renders in **both themes** and **both densities**, browser-verified; component
previews are built from `--btn-*`/`--field-*`/`--chip-*` alone and adapt across
themes with zero markup change; `python3 design/contrast.py` → **`TOTAL FAILURES: 0`**
(210 pairs, both themes, incl. protanopia/deuteranopia); no raw values in
`components.css`. Back-compat: the Phase-1 short role aliases (`--bg`, `--ink`,
`--primary`, …) are retained so existing chrome keeps working.

---

## Component & pattern reference

Phases 3–10 build the component and pattern library on top of the Phase 0–2 foundations above.
Each phase is documented in its own file under [`design/docs/`](./docs/) rather than inlined here
(they total ~2700+ lines; this section is the index, not a duplicate — see the Artifact Strategy
in `design-system-plan.md`).

- **Phase 3 — Core components** — layout, navigation, forms, data display, feedback, and overlays;
  ~80 components across six self-contained styleguide modules, built only from the Phase 2 token
  layer. Signature components: App Shell (3A), ⌘K Command Palette (3B), Stat Card + sortable Table
  (3D). [`phase-3a-layout.md`](./docs/phase-3a-layout.md) ·
  [`phase-3b-navigation.md`](./docs/phase-3b-navigation.md) ·
  [`phase-3c-forms.md`](./docs/phase-3c-forms.md) ·
  [`phase-3d-data-display.md`](./docs/phase-3d-data-display.md) ·
  [`phase-3e-feedback.md`](./docs/phase-3e-feedback.md) ·
  [`phase-3f-overlays.md`](./docs/phase-3f-overlays.md)
- **Phase 4 — AI components** — agent status/cards/timeline/dependency-graph (4A); execution
  timeline/debate/judgment/approval/streaming-console/tool-inspection (4B);
  streaming-text/token-bar/prompt-inspector (4C) — the differentiator layer, built on the `--ai-*`
  AI-state tokens. [`phase-4a-agents.md`](./docs/phase-4a-agents.md) ·
  [`phase-4b-execution.md`](./docs/phase-4b-execution.md) ·
  [`phase-4c-llm.md`](./docs/phase-4c-llm.md)
- **Phase 5 — Workflow & CLI components** — task status/cards/milestones/timeline/pipeline-view/
  workflow-graph/dependency-graph/execution-queue (5A), reframed around the
  roadmap/initiative-planning domain (`Initiative`/`Feature`/`RoadmapItem`,
  `WorkflowService.evaluate_initiative`); command badge/exit status/ANSI
  renderer/console/terminal/copy/history/suggestion/live-streaming output for the
  `productagents` CLI (5B). [`phase-5a-workflow.md`](./docs/phase-5a-workflow.md) ·
  [`phase-5b-cli.md`](./docs/phase-5b-cli.md)
- **Phase 6 — Project components** — Workspace Selector, Project Card, Repository Card, Git
  Status, Branch Badge, Directory Tree, File Explorer, File Preview, Recent Projects; grounded in
  `WorkspaceService.list`/`resolve` and the GitHub connector's `owner/repo` where a real shape
  exists. [`phase-6-project.md`](./docs/phase-6-project.md)
- **Phase 7 — Settings** — Settings Navigation, Section, Preference Card, Theme Selector,
  Keyboard-Shortcut Editor, Provider/Model Configuration, MCP Configuration, Environment-Variable
  Editor, API Key Input; Provider/Model Configuration and API Key Input grounded in the real
  `config.get`/`config.set` contract, with a security review confirming the key/secret inputs
  never hold a fetched value. [`phase-7-settings.md`](./docs/phase-7-settings.md)
- **Phase 8 — Monitoring & observability** — Event Timeline, Metrics Card, Resource/Memory/Token
  Usage, Execution Statistics, Cost Dashboard, Performance Graph, Health Indicator; Event
  Timeline/Execution Statistics/Performance Graph/Health Indicator grounded in the real
  `platform.events.Event` taxonomy and `Session` shape via `SessionService`.
  [`phase-8-monitoring.md`](./docs/phase-8-monitoring.md)
- **Phase 9 — Empty & transitional states** — First-Run Experience, Empty Collection State
  (workspace/agents/projects/executions/no-results), Initial Loading, Offline Mode, Maintenance
  State; illustration stance recorded as **no illustrations — empty states are structural** (icon
  + copy + primary action). [`phase-9-empty-states.md`](./docs/phase-9-empty-states.md)
- **Phase 10 — Design patterns** — Flow & risk patterns: confirmation flows, undo, progressive
  disclosure, wizards (10A); Direct-manipulation & editing patterns: inline editing, drag-and-drop,
  bulk actions, contextual menus (10B); System & recovery patterns: error recovery, notification
  strategy, sync status, conflict resolution (10C). Notification Strategy reuses Phase 3E's
  `.fbk-*` feedback classes rather than a parallel toast system.
  [`phase-10a-flow-patterns.md`](./docs/phase-10a-flow-patterns.md) ·
  [`phase-10b-editing-patterns.md`](./docs/phase-10b-editing-patterns.md) ·
  [`phase-10c-system-patterns.md`](./docs/phase-10c-system-patterns.md)

## Documentation template

Every component/pattern documented from Phase 3 onward satisfies this 14-point per-item template
(finalized in Phase 11): Purpose · When to use · When not to use · Anatomy · Variants · Sizes ·
States · Accessibility requirements · Keyboard interactions · Content guidelines · Visual examples
· Do's and don'ts · Implementation notes · React API · Design tokens used.

Two dimensions are satisfied once per file, not once per component:
- **React API** — these are gallery/demo components in `design/styleguide/src/`, not yet a
  published library, so each file carries exactly one line near the top instead of a props table
  per component, e.g. "React API: not yet productized — each component here is a
  `design/styleguide/src/phaseN/` demo; a stable public API is defined when it migrates to
  `desktop/src/ui/`."
- **Visual examples** — satisfied by the single "Live gallery: ..." / "Files: ..." pointer near
  the top of each file, identifying the `.tsx`/`.css` source and the styleguide gallery section.
