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

React API: not yet productized — each component here is a
`design/styleguide/src/phase4/` demo; a stable public API is defined when it
migrates to `desktop/src/ui/`.

---

## Streaming Text

- **Purpose** — text that builds progressively with a blinking cursor,
  used anywhere token-by-token model output is displayed.
- **When to use / not** — inline, token-by-token model output. Not for a
  finished, static block of text — once streaming completes, treat it as
  plain text (this component's own `done` state handles the transition).
- **Anatomy** — `p4c-streaming-text` (inline span) wrapping the text plus a
  `p4c-streaming-text__cursor` that is omitted once `data-done="true"`.
- **Variants** — none.
- **Sizes** — single size; compact density reduces the font size.
- **States** — streaming (cursor visible, blinking) vs. done (cursor
  removed).
- **Keyboard** — none; inline text, not interactive.
- **Accessibility** — the blinking cursor is `aria-hidden`; the component has
  no `aria-live` region of its own, so incremental streamed updates aren't
  announced to screen readers — wrap it in one if that matters for the use
  case.
- **Content guidelines** — `text` is the raw model output streamed so far,
  rendered verbatim with no truncation or formatting applied.
- **Tokens** — `--ai-streaming` (cursor colour).

## Thinking Indicator

- **Purpose** — three staggered pulsing dots shown while the model is
  reasoning before streaming begins.
- **When to use / not** — the brief pre-streaming reasoning/tool/retrieval
  phase. Not for a phase already producing visible output — switch to
  Streaming Text once tokens start arriving.
- **Anatomy** — `p4c-thinking` (`role="status"`) → `p4c-thinking__dots` (3
  dots, staggered animation delay) + `p4c-thinking__label`.
- **Variants** — four actions, each with its own colour/label: reasoning
  (indigo, "Thinking"), tool (`--ai-tool`, "Calling tool"), retrieving
  (`--ai-done`, "Retrieving"), generating (`--ai-streaming`, "Generating").
- **Sizes** — single size; compact density shrinks the dots and reduces gap.
- **States** — a single animating state — the dots always pulse while
  mounted; there's no static/paused variant, unmount the component when the
  model stops thinking.
- **Keyboard** — none; not interactive.
- **Accessibility** — `role="status"` with an `aria-label` mirroring the
  visible label, so the state is announced even though the dots themselves
  are `aria-hidden`.
- **Content guidelines** — default labels are short gerund phrases
  ("Thinking", "Calling tool"...); the optional `label` override should stay
  similarly short since it also drives the `aria-label`.
- **Tokens** — `--p4c-thinking-color` (set per action from `--ai-thinking`/
  `--ai-tool`/`--ai-done`/`--ai-streaming`).

## Token Usage Bar

- **Purpose** — a three-segment stacked bar showing prompt vs. completion
  vs. remaining tokens against a context limit, with a legend and a warn
  state near the limit.
- **When to use / not** — per-call or per-run token accounting against a
  context limit. Not for cost — use Cost Indicator for dollar amounts.
- **Anatomy** — `p4c-token-bar` → `p4c-token-bar__track` (prompt segment +
  completion segment + transparent remainder) + `p4c-token-bar__legend`
  (dot + label + value per segment, plus a total readout).
- **Variants** — none.
- **Sizes** — single size; compact density reduces track height and legend
  gap.
- **States** — `data-warn="true"` (usage over 80% of limit) switches both
  filled segments to an amber tint and shows a "Near limit" pill.
- **Keyboard** — none; static display.
- **Accessibility** — the track carries `role="img"` with an `aria-label`
  summarizing used vs. limit tokens, so the visual bar has a text equivalent.
- **Content guidelines** — token counts are comma-grouped
  (`toLocaleString()`); the warn pill's text is fixed ("Near limit"), not
  configurable per instance.
- **Implementation notes** — the 80% warn threshold is hardcoded in the
  component (`used / limit > 0.8`), not exposed as a prop.
- **Tokens** — `--ai-thinking` (prompt segment), `--ai-analyst-analytics`
  (completion segment), `--ai-confidence-track`, `--ai-degraded`/
  `-degraded-text` (warn state).

## Cost Indicator

- **Purpose** — two variants for showing model spend: a compact inline badge
  and a full breakdown panel per model.
- **When to use / not** — `CostBadge` inline in text/lists, `CostPanel` for a
  full per-model breakdown in a run detail view. Not for token counts — use
  Token Usage Bar for that.
- **Anatomy** — `p4c-cost-badge` (inline pill, `$0.0901`-style) — and —
  `p4c-cost-panel` → head (model name + total) + `<dl>` rows (`p4c-cost-panel
  __row`) of label, proportional bar, token count, percentage, and dollar
  value, one row per cost category (prompt, completion).
- **Variants** — `CostBadge` (inline pill) and `CostPanel` (block
  breakdown); pick one per context, not both for the same figure.
- **Sizes** — single size; compact density reduces panel row padding/gap.
- **States** — none; static figures, no hover/interactive state.
- **Keyboard** — none; not interactive.
- **Accessibility** — each panel row's proportional bar is `aria-hidden`;
  the percentage and dollar value are always shown as text alongside it.
- **Content guidelines** — dollar amounts are always shown to 4 decimal
  places (`$0.0901`) since per-call costs are often sub-cent; don't round to
  2 decimals.
- **Tokens** — `--accent`/`--accent-text` (badge), `--p4c-cost-color` (per
  row, `--ai-analyst-customer`/`--ai-analyst-analytics`), `--p4c-cost-pct`.

## Context Window Viewer

- **Purpose** — a stacked, legended bar showing how the model's context
  window is allocated across named segments (e.g. system prompt, history,
  current input) plus remaining available space.
- **When to use / not** — how a model's context window is allocated across
  named segments (system/history/input) for a single call. Not for
  cumulative usage across a whole run — use Token Usage Bar for
  prompt/completion totals.
- **Anatomy** — `p4c-ctx-window` → `p4c-ctx-window__track` (one
  `p4c-ctx-window__seg` per named segment + a transparent `--avail`
  remainder) + `p4c-ctx-window__legend` (dot + label + token value per
  segment, plus a usage readout).
- **Variants** — none; segments are caller-supplied data, not a variant prop.
- **Sizes** — single size; compact density reduces track height.
- **States** — none; static display.
- **Keyboard** — none; not interactive.
- **Accessibility** — the track carries `role="img"` with an `aria-label`
  summarizing used vs. limit tokens, mirroring Token Usage Bar.
- **Content guidelines** — segment labels are short (System/History/Input);
  token values are comma-grouped.
- **Tokens** — `--p4c-ctx-color` (per segment, caller-supplied `--ai-*`
  colour), `--ai-confidence-track`, `--border-subtle` (available segment).

## Prompt Inspector

- **Purpose** — an expandable panel for viewing a prompt template's raw
  body, with `{{variable}}` placeholders highlighted.
- **When to use / not** — viewing a prompt template's raw body with its
  version, e.g. in a prompt-registry/admin view. Not for comparing two
  versions — use Prompt Diff for that.
- **Anatomy** — `p4c-prompt-inspector` → `p4c-prompt-inspector__toggle`
  button (CSS chevron + name + version meta) that reveals a `<pre><code>`
  body with `p4c-prompt-var` spans around each `{{var}}`.
- **Variants** — none.
- **Sizes** — single size; compact density reduces toggle and body padding.
- **States** — collapsed / expanded (`data-open`), toggle hover/focus-visible.
- **Keyboard** — the toggle is a real `button` with `aria-expanded`.
- **Accessibility** — `aria-expanded` on the toggle communicates disclosure
  state to assistive tech.
- **Content guidelines** — only `{{double-brace}}` placeholders are
  highlighted — any other bracket style renders as plain text; version is
  shown as `v{n}` (e.g. "v3").
- **Tokens** — `--accent-text` (variable highlight), `--text-terminal`
  (monospace body), `--surface-raised/-sunken`.

## Prompt Diff

- **Purpose** — a unified diff between two prompt versions, with added/
  removed/context lines visually distinguished.
- **When to use / not** — comparing two prompt template versions inline. Not
  for viewing a single version's full body — use Prompt Inspector for that.
- **Anatomy** — `p4c-diff` → header (diff label) + `p4c-diff__body` of
  `p4c-diff__line` rows, each with a `p4c-diff__gutter` glyph (`+`/`-`/space)
  and the line text.
- **Variants** — `p4c-diff__line--{added|removed|context}`.
- **Sizes** — single size; compact density reduces line min-height and
  removes vertical padding.
- **States** — none; a static diff view.
- **Keyboard** — none; not interactive.
- **Accessibility** — the diff container carries an `aria-label`; line type
  is conveyed by the gutter glyph as well as colour (never colour alone).
- **Content guidelines** — blank lines pass a single space (`text: " "`) so
  the row keeps its height; the gutter is a literal `+`, `-`, or blank.
- **Tokens** — `--border-success` (added), `--border-error` (removed),
  `--text-terminal`.

## Prompt History

- **Purpose** — an ordered list of prompt versions: version number, date,
  character count, and a signed delta from the prior version; the active
  version is marked.
- **When to use / not** — the version list for one prompt template (e.g. the
  prompt registry view). Not for comparing two specific versions' content —
  use Prompt Diff for that.
- **Anatomy** — `p4c-prompt-history` (`<ol>`) of `p4c-prompt-history__item`
  rows (version, date, char count + delta pill, an "active" badge when
  `data-active="true"`).
- **Variants** — none.
- **Sizes** — single size; compact density reduces item padding.
- **States** — `data-active="true"` tints the row and shows the badge; the
  delta pill is signed (`data-sign="pos"`/`"neg"`).
- **Keyboard** — none; rows are plain `<li>` elements, not focusable or
  clickable.
- **Accessibility** — semantic `<ol>` conveys version order; the active
  version is marked with a text "active" badge, not background colour
  alone.
- **Content guidelines** — delta is always signed (`+42`, `-18`); version
  number is prefixed with "v".
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
- **Sizes** — single size; compact density reduces turn padding.
- **States** — none; a static, read-only transcript.
- **Keyboard** — none; turns aren't focusable or interactive.
- **Accessibility** — the container carries `aria-label="Conversation
  transcript"`; each turn's role is shown as uppercase text, not background
  tint alone.
- **Content guidelines** — turn content renders verbatim in `<pre>` (plain
  text or JSON, whatever was actually sent/received); token count is
  optional and only shown when known.
- **Tokens** — `--ai-thinking` (system tint), `--ai-done`/`-done-text`
  (assistant tint), `--accent-text` (user role label), `--text-terminal`.

---

No new tokens are declared by `phase4c-llm.css` — it has no `:root` block.
All LLM-state colour comes from the existing `--ai-*` semantic tokens; the
`--p4c-*` custom properties referenced above are per-instance values set
inline via `style={}` in the TSX, not entries in the token layer.
