# ProductAgents Design System — Phased Build Plan

> **For each session:** read [`design-system-context.md`](./design-system-context.md) **first**,
> then the one phase you are executing below. Apply the `frontend-design`, `impeccable`, and
> `ui-ux-pro-max` skills throughout. One phase (or sub-phase) per session — finish, verify, sign
> off, then stop. This supersedes the brainstorm in `design-system-phases.md`.

**Goal:** Build a clean, modern, accessible, token-driven design system for ProductAgents —
incrementally and verifiably — so every current and future surface (desktop GUI + CLI) is visually
and behaviorally consistent.

**Architecture:** A layered token system (primitive → semantic → component → state → theme) expressed
as CSS custom properties, plus a component library and a **browser-rendered styleguide** that is the
review surface. Built phase by phase; each phase is seen, critiqued, and signed off before the next.

**Tech stack:** TypeScript, React, CSS custom properties (the token transport), Vite (styleguide dev
server), Vitest (logic tests), OSS fonts shipped locally. Python only for `contrast.py` (the WCAG/CVD
gate). Target consumer: the Tauri + React desktop app.

## Global constraints (apply to every phase)

- **WCAG 2.1 AA** — body ≥ 4.5:1, large/UI/structural ≥ 3:1 — computed by `design/contrast.py`,
  including protanopia/deuteranopia simulation; CI gate is `TOTAL FAILURES: 0`. **Never assert a ratio.**
- **Color is never the only channel** (WCAG 1.4.1): pair every semantic color with glyph/label/position/border.
- **Dark-first + a required light theme**; dark is primary; **never pure `#000`** (off-black). High-contrast theme optional/later.
- **Keyboard-first**; every interactive surface fully operable without a mouse.
- **Density: comfortable + compact**, must stay legible for 60–90 min.
- **No raw values in components** — reference tokens only. New need = new *semantic token/role*, never a literal.
- **OSS fonts that ship locally**; no runtime web-font fetch; no exotic deps; implementation-friendly for React + Tauri.
- **Render and review** every deliverable in a browser via the styleguide; do **not** rely on Pencil screenshots (see context §7).
- **Beat the AI-slop reflexes** (context §9) and run the two-altitude slop test on the system.

---

## How to run a phase session (execution protocol)

1. **Load context.** Read `design-system-context.md`, then this phase's section.
2. **Invoke the skills.** `frontend-design` + `impeccable` + `ui-ux-pro-max` (e.g. `ui-ux-pro-max`
   `--design-system`/`--domain` searches; `impeccable shape` to plan, then `critique`/`audit` to review).
3. **Brainstorm before building** (especially Phase 0/1): propose, critique against the brief, take a
   justified aesthetic risk, iterate — show the user only higher-confidence options.
4. **Build the slice** into the agreed homes (see *Artifact strategy*). Keep files small and focused.
5. **Verify** (the per-phase Definition of Done + the cross-cutting gates below): render in the
   styleguide, run `contrast.py`, run a11y checks, run a skill-based self-critique (`impeccable critique`).
6. **Update the Progress Tracker** in this file (check the box, note the date/commit).
7. **Present for sign-off** with the rendered styleguide; do not start the next phase until confirmed.
8. For **component-heavy** sub-phases, optionally use `superpowers:subagent-driven-development` /
   `superpowers:executing-plans` to run the sub-phase's tasks with per-task review.

### Cross-cutting Definition of Done (every phase)
- [ ] Deliverable renders correctly in the styleguide (light **and** dark), reviewed in a browser.
- [ ] `python3 design/contrast.py` → `TOTAL FAILURES: 0` (extend `PAIRS` for any new color).
- [ ] No raw hex/size/duration/z-index in any component — tokens only.
- [ ] Keyboard + focus + reduced-motion behavior specified/working; color not the only channel.
- [ ] `impeccable critique` + `frontend-design` slop check run; findings resolved or logged.
- [ ] Documented (purpose, variants, states, a11y, tokens used) per the doc template (Phase 11 format).

---

## Artifact strategy (confirm exact homes in Phase 0; these are the recommended defaults)

- **Tokens (source of truth):** `design/tokens/*.css` (CSS custom properties), layered:
  `primitives.css` → `semantic.css` → `components.css` → `themes/{dark,light}.css`. Optional
  `tokens.ts` type/union exports for autocomplete. The desktop app imports these later.
- **Styleguide (the review surface):** a small standalone **Vite + React + TS** app at
  `design/styleguide/` that imports the tokens and components and renders swatches, scales, component
  galleries, and AI-pattern demos. Run with `npm run dev` there. *This is what each phase is reviewed in.*
- **Components:** `design/styleguide/components/<Component>/` (component + spec + story) during design;
  migrate to `desktop/src/ui/` when adopting into the app (a later, separate step — this plan builds
  the system + styleguide, it does **not** rewrite product screens).
- **Contrast gate:** `design/contrast.py` (exists; keep and extend).
- **Living reference doc:** rewrite `design/DESIGN.md` incrementally as phases land (or keep per-phase
  docs), following the Phase 11 documentation template.
- **Pencil `.pen`:** optional secondary visual spec only; not the review surface (see context §7).

> Why a standalone styleguide and not the app: it isolates design iteration from product screens
> (honoring "not a screen redesign"), renders with real fonts in a real browser (fixing v0's broken
> verification), and is trivially reviewable. Phase 0 may instead choose an in-app `/styleguide` route.

---

## Progress tracker

- [x] **Phase 0** — Direction & setup (keystone; do first) — *"Instrument" direction signed off 2026-06-29; light default (owner override); styleguide harness at `design/styleguide/`; v0 archived to `design/_v0/`.*
- [x] **Phase 1** — Foundation primitives — *done 2026-06-29; `tokens/primitives.css` (7 OKLCH ramps + type/space/radius/elevation/motion/z/size scales) + `tokens/themes/{dark,light}.css` scaffold; IBM Plex Sans/Mono shipped local; Foundations gallery in styleguide; `contrast.py` rewired to Instrument palette → 0 failures.*
- [x] **Phase 2** — Token architecture (2A color · 2B type · 2C dimensional · 2D layout/interaction · 2E semantic+state · 2F AI-specific · 2G accessibility · 2H theme mapping) — *done 2026-06-29; `tokens/semantic.css` (non-color: type styles + dimensional + layout/interaction/focus + density + a11y) + `tokens/components.css` (component sets + 11-state matrix) + expanded `themes/{dark,light}.css` (all color roles + feedback + AI tokens, grounded in the real event vocabulary); icon set locked = **Phosphor**; `contrast.py` → 0 failures (210 pairs, both themes + CVD); token-reference gallery (by sub-phase) renders both themes/densities. Decision: color semantic tokens live in the theme files (the 2H "themes redefine only color" contract), non-color in semantic.css.*
- [x] **Phase 3** — Core components (3A layout · 3B navigation · 3C forms · 3D data display · 3E feedback · 3F overlays) — *done 2026-06-29; ~80 components across six self-contained styleguide modules (`src/phase3/Phase3*.tsx` + `phase3{a–f}-*.css`, prefixed `la-/nv-/fm-/dd-/fbk-/ov-`), each documented in `design/docs/phase-3*.md`. Built only from the Phase-2 token layer (no new colors → `contrast.py` still 0 failures, both themes + CVD); both themes + densities adapt with zero markup change; keyboard-operable; SVG-only icons; reduced-motion guards. Signature components: App Shell (3A), ⌘K Command Palette (3B), Stat Card + sortable Table (3D). Rendered + reviewed in the styleguide (light + dark). `App.tsx`/`main.tsx` wire the six modules; shared `sg.tsx` (Section + Specimen) + `.sg-subband`/`.sg-specimen` harness helpers.*
- [x] **Phase 4** — AI components (4A agent · 4B execution · 4C LLM) — *done 2026-06-30 (PR #78); agent status/cards/timeline/dependency-graph (4A), execution timeline/debate/judgment/approval/streaming-console/tool-inspection (4B), streaming-text/token-bar/prompt-inspector (4C) across `src/phase4/Phase4*.tsx` + `phase4{a–c}-*.css`, prefixed `p4a-/p4b-/p4c-`, each documented in `design/docs/phase-4*.md`. Built only from the Phase-2 token layer + `--ai-*` AI-state tokens (no new colors → `contrast.py` still 0 failures); both themes + densities; reduced-motion guards on all pulse/stream/blink animations.*
- [x] **Phase 5** — Workflow & CLI components (5A workflow · 5B CLI) — *done 2026-06-30; reframed around the roadmap/initiative-planning domain (Initiative/Feature/RoadmapItem, `InitiativeStatus`/`FeatureStatus`/`Priority` from `pa-core`, `WorkflowService.evaluate_initiative`, `ConnectorService.sync`) rather than duplicating Phase 4's AI-run surface — task status/cards/milestones/timeline/pipeline-view/workflow-graph/dependency-graph/execution-queue (5A), command badge/exit status/ANSI renderer/console/terminal/copy/history/suggestion/live-streaming output for the `productagents` CLI (5B), across `src/phase5/Phase5*.tsx` + `phase5{a,b}-*.css`, prefixed `p5a-/p5b-`, each documented in `design/docs/phase-5*.md`. Built only from the Phase-2/4 token layer (no new colors → `contrast.py` still 0 failures); both themes + densities verified live in-browser (found and fixed a missing `stroke="currentColor"` on both phases' local Icon components, which left glyphs invisible); reduced-motion guards on cursor/suggest blink animations.*
- [x] **Phase 6** — Project components — *done 2026-06-30; Workspace Selector, Project Card, Repository Card, Git Status, Branch Badge, Directory Tree, File Explorer, File Preview, Recent Projects across `src/phase6/Phase6Project.tsx` + `phase6-project.css`, prefixed `p6-`, documented in `design/docs/phase-6-project.md`. Grounded in real shapes where they exist (`WorkspaceService.list/resolve`, GitHub connector `owner/repo`); git/file-tree state is forward-looking. Built only from the Phase-2 token layer (no new colors → `contrast.py` still 0 failures); status hues correctly use `--signal`/`--signal-text` for amber rather than the nonexistent `--warning` literal (a pre-existing bug in Phase 5's `PriorityBadge`, left as-is — out of scope here). Both themes + densities verified live in-browser; keyboard-operable (tree rows, workspace list, recent-projects rows all real/focusable elements with visible focus rings).
- [x] **Phase 7** — Settings — *done 2026-06-30; Settings Navigation, Section, Preference Card, Theme Selector, Keyboard-Shortcut Editor, Provider/Model Configuration, MCP Configuration, Environment-Variable Editor, API Key Input across `src/phase7/Phase7Settings.tsx` + `phase7-settings.css`, prefixed `p7-`, documented in `design/docs/phase-7-settings.md`. Provider/Model Configuration and API Key Input grounded in the real `config.get`/`config.set` contract (`ConfigStatus`/`ProviderInfo`, `desktop/src/panels/SettingsPanel.tsx`); Theme Selector/Keyboard-Shortcut Editor/MCP Configuration/Environment-Variable Editor are forward-looking, no backend yet. Security review: API Key Input and secret env-var rows never hold a fetched value — the field starts empty every render and the reveal toggle is disabled while empty, so only locally-typed text can ever be shown. Built only from the Phase-2 token layer (no new colors → `contrast.py` still 0 failures); both themes + densities verified live in-browser; keyboard-operable (every control is a real button/input/select; the shortcut editor's capture mode cancels on Escape).*
- [x] **Phase 8** — Monitoring & observability — *done 2026-06-30; Event Timeline, Metrics Card, Resource/Memory/Token Usage, Execution Statistics, Cost Dashboard, Performance Graph, Health Indicator across `src/phase8/Phase8Monitoring.tsx` + `phase8-monitoring.css`, prefixed `p8-`, documented in `design/docs/phase-8-monitoring.md`. Event Timeline/Execution Statistics/Performance Graph/Health Indicator grounded in the real `platform.events.Event` taxonomy + `Session` shape via `SessionService` (latency computed from real `ts` deltas — the only timing signal the Event Store persists); Resource/Memory/Token Usage and Cost Dashboard have no backend schema yet — forward-looking, like Phase 6's git/file-tree state. First real consumer of the Phase-2 `--timeline-*` component tokens; reuses `--gauge-*` (Phase 4C). Built only from the existing token layer (no new colors → `contrast.py` still 0 failures); both themes + densities verified live in-browser (caught and fixed a CSS Grid `1fr` track collapsing to 0 under the Specimen harness's flex layout — Cost Dashboard's bars were invisible until fixed with an explicit container width).*
- [x] **Phase 9** — Empty & transitional states — *done 2026-06-30; First-Run Experience, Empty Collection State (workspace/agents/projects/executions/no-results), Initial Loading, Offline Mode, Maintenance State across `src/phase9/Phase9EmptyStates.tsx` + `phase9-empty-states.css`, prefixed `p9-`, documented in `design/docs/phase-9-empty-states.md`. Illustration stance recorded: no illustrations — empty states are structural (icon + copy + primary action), per Phase 3E's `.fbk-state` precedent. Empty Workspace/Executions grounded in `WorkspaceService`/`SessionService`; Offline reuses Phase 3E's sidecar framing; Empty Agents/Projects, First-Run, No Search Results, Initial Loading, and Maintenance State are forward-looking, same posture as Phase 6/8. Built only from the existing token layer (no new colors → `contrast.py` still 0 failures); both themes + densities verified live in-browser; keyboard-operable; reduced-motion guards on the spinner and skeleton shimmer.*
- [x] **Phase 10** — Design patterns — *done 2026-06-30; Flow & risk patterns (confirmation flows, undo, progressive disclosure, wizards) across `src/phase10/Phase10AFlowPatterns.tsx` + `phase10a-flow-patterns.css`, Direct-manipulation & editing patterns (inline editing, drag-and-drop, bulk actions, contextual menus) across `Phase10BEditingPatterns.tsx` + `phase10b-editing-patterns.css`, and System & recovery patterns (error recovery, notification strategy, sync status, conflict resolution) across `Phase10CSystemPatterns.tsx` + `phase10c-system-patterns.css`, prefixed `p10a-/p10b-/p10c-`, documented in `design/docs/phase-10{a,b,c}-*.md`. Notification Strategy reuses Phase 3E's `.fbk-*` feedback classes rather than inventing a parallel toast system. Wired into `App.tsx` as a single "Design patterns" tab (graduated out of `SOON`) rendering all three modules in sequence — no A/B/C sub-nav, matching every prior phase's shallow one-tab-per-category pattern. Phase 10B's review caught and fixed two issues before merge: a raw `20rem` literal replaced with the `--width-inspector` token, and a missing `:focus-visible` state on the bulk-action checkboxes. Built only from the existing token layer (no new colors → `contrast.py` still 0 failures); both themes + densities verified code-level (no raw hex in any `phase10*.css`, all three components take the same `density` prop as siblings); keyboard-operable per Tasks 1–3's per-task review.*
- [ ] **Phase 11** — Documentation

---

## Phase 0 — Direction & setup  *(keystone — must be first)*

**Objective:** Lock the visual direction (with explicit sign-off), stand up the verification harness,
and confirm the artifact homes — so every later phase builds on a confirmed, reviewable foundation.

**Depends on:** nothing. **Read first:** context §§1–11; skim `design/DESIGN.md` + `design-system.pen` as v0 input.

**Tasks:**
1. Using `frontend-design`: write the scene sentence, define 2–3 candidate directions (the v0 "The
   Record" is one input — keep/adjust/replace), each with palette intent, type pairing, density, and a
   signature element; run the two-altitude slop test. Present concept boards for the user to choose.
2. Stand up the **styleguide harness**: scaffold `design/styleguide/` (Vite + React + TS), wire local
   OSS fonts, add a dark/light theme toggle and a density toggle driven by `data-theme`/`data-density`.
3. Confirm artifact homes (tokens dir, styleguide, components dir, docs) — adjust the *Artifact
   strategy* above if the user prefers different locations.
4. Decide the fate of v0 artifacts (keep as reference / archive to `design/_v0/` / discard) — ask.

**Deliverables:** chosen direction (1 paragraph + palette/type intent) recorded at the top of
`design/DESIGN.md`; running `design/styleguide/` shell with theme + density toggles; confirmed homes.

**Skills:** `frontend-design` (direction, slop test), `ui-ux-pro-max --design-system` (sanity-check the
direction against product type), `impeccable shape` (plan the harness).

**Definition of Done / sign-off:** the user explicitly approves the visual direction; the empty
styleguide renders in a browser with working theme/density toggles. **Do not proceed without sign-off.**

---

## Phase 1 — Foundation primitives

**Objective:** The raw primitive values everything derives from — *not yet semantic*.

**Depends on:** Phase 0. **Read first:** context §§7–9; the chosen direction.

**Tasks:** define primitive scales as CSS custom properties in `design/tokens/primitives.css`:
- Color **ramps** (e.g. `--c-slate-{50..900}`, brand ramp, and each signal-hue ramp) — OKLCH-derived,
  hexes pinned; enough steps to compose semantic tokens and hover/active by step.
- Type primitives: font families (sans / mono / optional display), a font-size scale (xs…5xl), weights,
  line-heights (tight/normal/relaxed/loose), letter-spacing (tight/normal/wide).
- Spacing scale (0,2,4,6,8,12,16,20,24,32,40,48,64,80,96). Radii (none…full). Border widths
  (hairline/thin/medium/thick). Shadow/elevation primitives. Opacity tokens. Motion (durations + easings
  + presets). Z-index scale. Breakpoints. Blur. Size tokens (icon/avatar/button/input).
- Theme-system scaffold: how primitives feed `themes/{dark,light}.css` (light/dark; high-contrast later).

**Deliverables:** `design/tokens/primitives.css`; a **Foundations gallery** in the styleguide rendering
every ramp/scale (swatches, type specimens, spacing/radius/elevation samples, motion demos).

**Skills:** `frontend-design` (palette/type craft, anti-slop), `ui-ux-pro-max --domain color/typography`,
`impeccable` (contrast realism, restraint).

**Definition of Done:** Foundations gallery renders in both themes; every color ramp step that will
carry text passes `contrast.py`; scales are complete and on-grid; **no off-scale values anywhere**.

---

## Phase 2 — Token architecture  *(semantic → component → state → theme)*

**Objective:** Map primitives into the layered token system that components actually consume. Run as
sub-phases (one session each); each renders a "token reference" gallery in the styleguide.

**Depends on:** Phase 1. **Read first:** the layered model in `design-system-phases.md` §"Token
Architecture"; context §5 (event vocabulary, citation contract) for the AI tokens.

- **2A — Color semantic tokens.** Background (primary/secondary/tertiary/elevated/overlay/inverse),
  Surface (default/raised/floating/selected/hover/pressed), Text (primary…info), Border
  (default/subtle/strong/focus/error/success/warning), Feedback (success/warning/error/info × bg/surface/
  border/text/icon). File: `design/tokens/semantic.css`.
- **2B — Typography text styles.** Composed styles (Display, Heading 1–4, Title, Body L/M/S, Caption,
  Label, Button, **Code**, **Terminal**) referencing Phase-1 primitives.
- **2C — Dimensional tokens.** Radius, border-width, elevation (Surface…Overlay, each shadow/blur/
  opacity/ambient/direction), motion, opacity, blur, size tokens — promoted to semantic names.
- **2D — Layout & interaction tokens.** Breakpoints (Compact/Medium/Expanded/Wide), content/sidebar/
  panel/dialog widths, grid (gaps/padding/section spacing), icon sizes+stroke, z-index (Base…Notification),
  focus (ring width/offset/color/shadow), interaction (cursors, transitions).
- **2D · Iconography (decision + tokens).** Choose the icon **set/library** here, before components consume
  it in Phase 3 — SVG only, never emoji (context §9; ui-ux-pro-max `no-emoji-icons`). Candidates: **Lucide**
  (ubiquitous, MIT, neutral) or **Phosphor** (more character, pairs with Plex's geometry). Lock one set, one
  stroke width, and the `icon-{xs…xl}` sizes (primitives exist from Phase 1) as tokens; document the usage
  rules (consistent stroke, filled-vs-outline discipline, ≥44px touch target, baseline alignment).
- **2E — Component + State tokens.** Per-component token sets; the state matrix (Default/Hover/Focus/
  Active/Selected/Disabled/Dragging/Loading/Invalid/Success/Warning/Error). File: `design/tokens/components.css`.
- **2F — AI-specific tokens.** Agent status (Idle…Cancelled), workflow (node/edge), execution timeline
  (running/completed/failed/waiting/retrying), log levels (trace…critical), streaming/thinking/approval —
  ProductAgents' differentiator. Ground in the real event vocabulary (context §5).
- **2G — Accessibility tokens.** Min contrast ratios, focus-indicator colors, reduced-motion variants,
  high-contrast alternatives, min interactive sizes (≥44px where touch applies), accessible color pairings.
- **2H — Theme mapping.** `themes/dark.css` + `themes/light.css` redefine semantic tokens only, so
  components adapt with zero changes. Verify both with `contrast.py`.

**Deliverables (per sub-phase):** the relevant `design/tokens/*.css`; a token-reference gallery section.

**Skills:** `ui-ux-pro-max` (semantic-token conventions, a11y), `impeccable` (states, contrast realism),
`frontend-design` (AI-token expressiveness without slop).

**Definition of Done:** components could be built using **only** these tokens; both themes pass
`contrast.py` (incl. CVD) for every text-on-background pair; the token reference renders in the styleguide.

---

## Phase 3 — Core components

**Objective:** The working component vocabulary. One sub-phase per session; each component documented
per the Phase 11 template (purpose, when/when-not, anatomy, variants, sizes, states, a11y, keyboard,
content, examples, do/don't, React API, tokens used).

**Depends on:** Phase 2. **Read first:** context §§4–6; relevant existing panel in `desktop/src/panels/`.

- **3A — Layout:** App Shell, Window Frame, Navigation Sidebar, Top Bar, Context Toolbar, Secondary
  Sidebar, Inspector Panel, Split/Resizable/Docked Panels, Workspace, Page Container, Section, Card,
  Surface, Divider, Scroll Area.
- **3B — Navigation:** Sidebar Nav, Tree View, Breadcrumbs, Tabs, **Command Palette**, Quick Switcher,
  Search Bar, Pagination, Stepper, Navigation Rail, Context Menu.
- **3C — Forms:** Button (+ Icon/Toggle/Link), Text/Search/Password/Number Input, Text Area, Select,
  Combobox, Multi-select, Checkbox, Radio, Toggle Switch, Slider, Date/Time Picker, File Upload, Form
  Field, Label, Help Text, Validation Message.
- **3D — Data display:** Table, Data Grid, List, Tree, Property/Description List, Badge, Tag, Chip,
  Avatar, Code Block, JSON Viewer, Key/Value Viewer, Stat/Metric Card, Timeline, Activity Feed, Diff
  Viewer, Markdown Renderer.
- **3E — Feedback:** Alert, Toast, Banner, Inline Message, Progress (bar/circular), Spinner, Skeleton,
  Empty/Error/Success/Warning State, Loading Overlay.
- **3F — Overlays:** Modal, Drawer, Popover, Tooltip, Hover Card, Context/Dropdown Menu, Command Dialog,
  Confirmation Dialog. (Mind overlay clipping/z-index/portal + scrim from tokens.)

**Skills:** `ui-ux-pro-max --domain ux` + `--stack react/shadcn` (patterns, a11y), `impeccable`
(states/craft/audit), `frontend-design` (signature components like the Command Palette).

**Definition of Done:** each component renders all variants/sizes/states in the styleguide (both
themes), is keyboard-operable, passes the cross-cutting DoD, and is documented.

---

## Phase 4 — AI components  *(the differentiator)*

**Objective:** The components that make ProductAgents unique — anchored to the real event vocabulary
and the streaming reasoning model (context §§1, 4, 5).

**Depends on:** Phase 3 (uses core components). **Read first:** context §5 (events, states, citation tiers).

- **4A — Agent:** Agent Card, Status Badge, Profile, Capability List, Selector, Timeline, Queue,
  Dependency Graph.
- **4B — Execution:** Execution Card, **Execution Timeline / streaming reasoning view** (the centerpiece —
  replaces the raw-JSON dump), Live Log Viewer, Streaming Console, Tool Execution Card, Tool Call
  Inspector, Tool Result Viewer, Execution Progress, Parallel Task Viewer, Retry Card, **Approval
  Request** (Approve/Reject/Request-analysis), Cancellation Banner, Resume Panel.
- **4C — LLM:** Streaming Text, Thinking Indicator, Token Usage, Cost Indicator, Context Window Viewer,
  Prompt Inspector, Prompt Diff, Prompt History, Conversation Viewer.

**Skills:** `frontend-design` (the signature streaming view — visualize reasoning, not chat),
`impeccable` (long-session density, honest loading/degraded/retry states), `ui-ux-pro-max` (timeline/log/chart patterns).

**Definition of Done:** the streaming reasoning view renders a realistic event sequence (waiting →
running → tool → debate → recommendation → judge → approval → done/degraded/failed) in the styleguide,
fully keyboard-operable, with the citation feature degrading per the data-contract tiers.

---

## Phase 5 — Workflow & CLI components

**Depends on:** Phase 3 (+ Phase 4 for shared status). **Read first:** context §§1, 4.

- **5A — Workflow:** Workflow Graph/Node/Edge, Stage Header, Progress Timeline, Pipeline View,
  Dependency Graph, Execution Queue, Task Card, Task Status, Milestone.
- **5B — CLI:** Terminal, Console Output, ANSI Renderer, Command History, Command Suggestion, Copy
  Output, Command Badge, Exit Status, Live Streaming Output. (The CLI is a peer client — keep parity.)

**Skills:** `ui-ux-pro-max` (graph/timeline patterns), `impeccable`, `frontend-design`.
**Definition of Done:** pipeline + CLI galleries render in both themes; pass cross-cutting DoD; documented.

---

## Phase 6 — Project components

**Objective:** ProductAgents-specific surfaces. Project Card, Repository Card, Git Status, Branch Badge,
File Explorer, Directory Tree, File Preview, Recent Projects, Workspace Selector.
**Depends on:** Phase 3. **Skills:** all three. **DoD:** cross-cutting DoD; documented; rendered both themes.

---

## Phase 7 — Settings

**Objective:** Settings Navigation, Section, Preference Card, Theme Selector, Keyboard-Shortcut Editor,
Provider/Model/MCP Configuration, Environment-Variable Editor, **API Key Input** (treat as
security-sensitive: never log/echo; mask; follow the platform's config.set path).
**Depends on:** Phase 3. **Read first:** `desktop/src/panels/SettingsPanel.tsx` (the one GUI write today).
**Skills:** all three. **DoD:** cross-cutting DoD; security review of the key/secret inputs; documented.

---

## Phase 8 — Monitoring & observability

**Objective:** Event Timeline, Metrics Card, Resource/Memory/Token Usage, Execution Statistics, Cost
Dashboard, Performance Graph, Health Indicator. Ground in the Event Store / Sessions data.
**Depends on:** Phases 3–4. **Skills:** `ui-ux-pro-max --domain chart` (data-viz a11y), `impeccable`, `frontend-design`.
**DoD:** charts have legends/tooltips/text alternatives, accessible (not color-only) palettes; cross-cutting DoD.

---

## Phase 9 — Empty & transitional states

**Objective:** First-Run Experience, Empty Workspace/Agents/Projects/Executions, No Search Results,
Initial Loading, Offline Mode, Maintenance State. Each is a *designed* state with a clear next action.

**Illustration stance (decide here).** ProductAgents is a telemetry "Instrument" — spot illustrations are
likely the wrong register; structured empty states (iconography + diagrams + copy + a primary action) do the
work. **Make an explicit decision in this phase:** either commit to a minimal illustration approach (define
the few assets + their style/format) or deliberately record **"no illustrations — empty states are
structural"** so it's a choice, not a silent gap. If any imagery is adopted, it must be themeable (light/dark)
and ship locally (no runtime fetch), consistent with the font/asset constraints.

**Depends on:** Phases 3–8 (uses their components). **Skills:** `impeccable onboard`, `frontend-design`,
`ui-ux-pro-max`. **DoD:** every empty/transitional state has copy + a primary action; the illustration stance
is recorded; cross-cutting DoD.

---

## Phase 10 — Design patterns

**Objective:** Reusable interaction patterns (beyond components): Confirmation flows, Destructive
actions, Long-running operations, Progressive disclosure, Multi-step workflows, Inline editing,
Keyboard-first interactions, Drag-and-drop, Selection, Bulk actions, Undo/redo, Error recovery,
Permission requests, Notification strategy.
**Depends on:** Phases 3–9. **Skills:** `impeccable` (UX patterns), `ui-ux-pro-max --domain ux`.
**Deliverable:** a Patterns section in the docs + interactive examples in the styleguide.
**DoD:** each pattern documented with do/don't + an example; consistent with the component library.

---

## Phase 11 — Documentation

**Objective:** Ensure every component/pattern is documented to a single template, and assemble the
canonical reference (rewrite/replace `design/DESIGN.md` as the living doc, or a docs site).

**Per-item template (use from Phase 3 onward, finalize here):** Purpose · When to use · When not to use ·
Anatomy · Variants · Sizes · States · Accessibility requirements · Keyboard interactions · Content
guidelines · Visual examples · Do's and don'ts · Implementation notes · React API · Design tokens used.

**Depends on:** all prior. **Skills:** `impeccable document`. **DoD:** every shipped component/pattern
has a complete doc entry; the reference is navigable and current.

---

## Highest-value, product-defining components (front-load attention)

From the owner's list — give these extra craft when their phase arrives:
1. **Command Palette** (primary navigation) — Phase 3B.
2. **Streaming Execution / reasoning view** (real-time agent progress) — Phase 4B.
3. **Workflow / Pipeline visualization** — Phase 5A.
4. **Tool Execution Cards** — Phase 4B.
5. **Live Log Console** (structured events) — Phase 4B.
6. **File Explorer + Diff Viewer** — Phases 6 / 3D.
7. **Resizable multi-panel workspace** — Phase 3A.
8. **AI conversation/context panels** (reasoning, prompts, approvals, history) — Phase 4.
9. **Project dashboard** (recent activity, tasks, summaries) — Phase 6 / 8.
10. **The token-based foundation** itself — Phases 1–2.

---

## Open decisions to resolve in Phase 0

1. **Visual direction** — keep / adjust / replace v0 "The Record"? (User found the v0 *result* poor.) → explicit sign-off.
2. **Artifact homes** — standalone `design/styleguide/` (recommended) vs an in-app `/styleguide` route; tokens in `design/tokens/` vs `desktop/src/styles/`.
3. **High-contrast theme** — in scope now or later?
4. **v0 artifacts** — keep as reference / archive to `design/_v0/` / discard?
5. **Pencil `.pen`** — maintain a `.pen` mirror, or rely solely on the rendered styleguide + docs? (Given the verification limits in context §7, the styleguide is primary regardless.)
