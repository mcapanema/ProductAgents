# Phase 4C — LLM Components

The UI vocabulary for raw LLM state and prompt management: streaming output,
thinking indicators, token accounting, cost display, context-window
inspection, prompt editing tools (inspector, diff, history), and a raw
conversation transcript view. Built only from the token layer — all LLM state
uses `--ai-*` tokens, and `overflow:hidden` is banned in favour of
`overflow:clip`. Live gallery: `styleguide` → 4C · LLM.

This phase has no local icon set — every component is built from text, CSS
shapes (e.g. the Prompt Inspector's chevron is a rotated CSS border, not an
SVG), and the shared status/colour system, with no `<svg>` icons of its own.

---

## Streaming Text

- **Purpose** — text that builds progressively with a blinking cursor,
  used anywhere token-by-token model output is displayed.
- **Anatomy** — `p4c-streaming-text` (inline span) wrapping the text plus a
  `p4c-streaming-text__cursor` that is omitted once `data-done="true"`.
- **States** — streaming (cursor visible, blinking) vs. done (cursor
  removed).
- **Tokens** — `--ai-streaming` (cursor colour).

## Thinking Indicator

- **Purpose** — three staggered pulsing dots shown while the model is
  reasoning before streaming begins.
- **Anatomy** — `p4c-thinking` (`role="status"`) → `p4c-thinking__dots` (3
  dots, staggered animation delay) + `p4c-thinking__label`.
- **Variants** — four actions, each with its own colour/label: reasoning
  (indigo, "Thinking"), tool (`--ai-tool`, "Calling tool"), retrieving
  (`--ai-done`, "Retrieving"), generating (`--ai-streaming`, "Generating").
- **Accessibility** — `role="status"` with an `aria-label` mirroring the
  visible label, so the state is announced even though the dots themselves
  are `aria-hidden`.
- **Tokens** — `--p4c-thinking-color` (set per action from `--ai-thinking`/
  `--ai-tool`/`--ai-done`/`--ai-streaming`).

## Token Usage Bar

- **Purpose** — a three-segment stacked bar showing prompt vs. completion
  vs. remaining tokens against a context limit, with a legend and a warn
  state near the limit.
- **Anatomy** — `p4c-token-bar` → `p4c-token-bar__track` (prompt segment +
  completion segment + transparent remainder) + `p4c-token-bar__legend`
  (dot + label + value per segment, plus a total readout).
- **States** — `data-warn="true"` (usage over 80% of limit) switches both
  filled segments to an amber tint and shows a "Near limit" pill.
- **Tokens** — `--ai-thinking` (prompt segment), `--ai-analyst-analytics`
  (completion segment), `--ai-confidence-track`, `--ai-degraded`/
  `-degraded-text` (warn state).

## Cost Indicator

- **Purpose** — two variants for showing model spend: a compact inline badge
  and a full breakdown panel per model.
- **Anatomy** — `p4c-cost-badge` (inline pill, `$0.0901`-style) — and —
  `p4c-cost-panel` → head (model name + total) + `<dl>` rows (`p4c-cost-panel
  __row`) of label, proportional bar, token count, percentage, and dollar
  value, one row per cost category (prompt, completion).
- **Tokens** — `--accent`/`--accent-text` (badge), `--p4c-cost-color` (per
  row, `--ai-analyst-customer`/`--ai-analyst-analytics`), `--p4c-cost-pct`.

## Context Window Viewer

- **Purpose** — a stacked, legended bar showing how the model's context
  window is allocated across named segments (e.g. system prompt, history,
  current input) plus remaining available space.
- **Anatomy** — `p4c-ctx-window` → `p4c-ctx-window__track` (one
  `p4c-ctx-window__seg` per named segment + a transparent `--avail`
  remainder) + `p4c-ctx-window__legend` (dot + label + token value per
  segment, plus a usage readout).
- **Tokens** — `--p4c-ctx-color` (per segment, caller-supplied `--ai-*`
  colour), `--ai-confidence-track`, `--border-subtle` (available segment).

## Prompt Inspector

- **Purpose** — an expandable panel for viewing a prompt template's raw
  body, with `{{variable}}` placeholders highlighted.
- **Anatomy** — `p4c-prompt-inspector` → `p4c-prompt-inspector__toggle`
  button (CSS chevron + name + version meta) that reveals a `<pre><code>`
  body with `p4c-prompt-var` spans around each `{{var}}`.
- **States** — collapsed / expanded (`data-open`), toggle hover/focus-visible.
- **Keyboard** — the toggle is a real `button` with `aria-expanded`.
- **Accessibility** — `aria-expanded` on the toggle communicates disclosure
  state to assistive tech.
- **Tokens** — `--accent-text` (variable highlight), `--text-terminal`
  (monospace body), `--surface-raised/-sunken`.

## Prompt Diff

- **Purpose** — a unified diff between two prompt versions, with added/
  removed/context lines visually distinguished.
- **Anatomy** — `p4c-diff` → header (diff label) + `p4c-diff__body` of
  `p4c-diff__line` rows, each with a `p4c-diff__gutter` glyph (`+`/`-`/space)
  and the line text.
- **Variants** — `p4c-diff__line--{added|removed|context}`.
- **Accessibility** — the diff container carries an `aria-label`; line type
  is conveyed by the gutter glyph as well as colour (never colour alone).
- **Tokens** — `--border-success` (added), `--border-error` (removed),
  `--text-terminal`.

## Prompt History

- **Purpose** — an ordered list of prompt versions: version number, date,
  character count, and a signed delta from the prior version; the active
  version is marked.
- **Anatomy** — `p4c-prompt-history` (`<ol>`) of `p4c-prompt-history__item`
  rows (version, date, char count + delta pill, an "active" badge when
  `data-active="true"`).
- **States** — `data-active="true"` tints the row and shows the badge; the
  delta pill is signed (`data-sign="pos"`/`"neg"`).
- **Tokens** — `--accent`/`--accent-text` (active badge), `--ai-done`/
  `-done-text` (positive delta), `--ai-failed`/`-failed-text` (negative
  delta).

## Conversation Viewer

- **Purpose** — a raw inspection transcript of the exact messages sent to and
  received from the model — explicitly **not** a chat UI.
- **When to use / not** — debugging/audit views of the literal prompt/
  response exchange. Not for a user-facing chat experience.
- **Anatomy** — `p4c-conv` → header label + `p4c-conv__turns` (`<ol>`) of
  `p4c-conv__turn` rows, each with a role row (role label + optional token
  count) and a `<pre><code>` content block.
- **Variants** — three roles, each background/role-label tinted differently:
  system (indigo), user (neutral card background), assistant (teal).
- **Tokens** — `--ai-thinking` (system tint), `--ai-done`/`-done-text`
  (assistant tint), `--accent-text` (user role label), `--text-terminal`.

---

No new tokens are declared by `phase4c-llm.css` — it has no `:root` block.
All LLM-state colour comes from the existing `--ai-*` semantic tokens; the
`--p4c-*` custom properties referenced above are per-instance values set
inline via `style={}` in the TSX, not entries in the token layer.
