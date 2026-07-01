# Phase 5B — CLI

Terminal chrome and command-output primitives for the `productagents` CLI:
history, autocomplete, streaming output, and ANSI-style status coloring.
Reuses the same "always-dark terminal surface" pattern Phase 4B established
for `StreamingConsole` (`--surface-sunken` regardless of theme, `--ai-log-*`
tones, `--text-terminal`/`--text-code` fonts) — no new tokens. Live gallery:
`styleguide` → Workflow & CLI → 5B.

Icons are inline SVG (`viewBox 0 0 24 24`, `stroke currentColor`,
`stroke-width 1.75`, round caps), defined locally in `Phase5CLI.tsx`.

React API: not yet productized — each component here is a
`design/styleguide/src/phase5/` demo; a stable public API is defined when it
migrates to `desktop/src/ui/`.

---

## Command Badge

- **Purpose** — inline monospace chip naming a CLI subcommand (`run`, `sync`,
  `sessions list`, `reflect`).
- **When to use / not** — referencing a command name inline in prose or a UI
  label. Not for the command-history rows themselves (those use
  `p5b-history__cmd`, unboxed, for scanability in a list).
- **Anatomy** — `p5b-cmd-badge`, a `<code>` element.
- **Variants** — none; a single chip style.
- **Sizes** — single size; no compact-density override defined.
- **States** — none; a static, non-interactive inline element.
- **Keyboard** — none; a `<code>`, not a button/link — not focusable.
- **Accessibility** — none beyond default `<code>` semantics; no ARIA needed
  since it's inline reference text, not interactive.
- **Content guidelines** — text is the literal subcommand string, including
  multi-word forms (e.g. "sessions list") — not abbreviated.
- **Tokens** — `--surface-sunken`, `--border-subtle`, `--radius-control`,
  `--text-code`.

## Exit Status

- **Purpose** — process exit code indicator: success (0) vs. failure
  (nonzero), icon + label + code.
- **When to use / not** — attached to any completed command invocation (a
  history row, a console block's summary line).
- **Anatomy** — `p5b-exit-status` inline group: check/x icon + "exit N" text.
- **Variants** — none; a single layout, `data-ok` boolean drives icon/color
  only.
- **Sizes** — single size; no compact-density override defined.
- **States** — `data-ok="true"` (success, `--ai-done` family) vs. the default
  failure state (`--ai-failed`).
- **Keyboard** — none; a static, non-interactive span.
- **Accessibility** — icon + text together, never color alone.
- **Content guidelines** — label is always the literal "exit N" (e.g. "exit
  0", "exit 1") — not a custom message.
- **Tokens** — `--ai-failed`, `--ai-done-text`, `--ai-done`, `--fw-semibold`.

## ANSI Renderer

- **Purpose** — renders a sequence of tokenized text spans with simulated
  ANSI-style tones (info/warn/error/done/dim), the way colorized CLI output
  would render in a real terminal.
- **When to use / not** — reproducing multi-tone CLI output (progress lines
  with mixed ✓/⚠/✗ markers) as static, accessible text rather than raw escape
  codes. Not for live/streaming text — see `LiveStreamingOutput`.
- **Anatomy** — `p5b-ansi` wraps `AnsiToken[]`, each rendered as a `<span>`
  with a `p5b-ansi--<tone>` class when a tone is set.
- **Variants** — none; tone is per-token (`AnsiToken.tone`), not a
  component-level variant.
- **Sizes** — single size; the component itself carries no font/spacing
  CSS — those come from whatever wraps it (e.g. the gallery's
  `.p5b-ansi-block` `<pre>`).
- **States** — each token independently carries a tone (info/warn/error/
  done/dim, or none); the component has no state beyond its `tokens` prop.
- **Keyboard** — none; static text output.
- **Accessibility** — tone is color-only inside the component itself — no
  icon accompanies `p5b-ansi--<tone>`. The sample's ✓/⚠/✗ glyphs are plain
  characters embedded in the token `text`, not something the component
  guarantees; callers must include a non-color glyph in `text` for a11y
  parity with Exit Status/Task Status's icon+text pattern.
- **Content guidelines** — tokens can embed literal newlines (`"\n"`) for
  multi-line output, as in `ANSI_SAMPLE`; include a glyph in `text` if a
  non-color tone signal is needed (see Accessibility).
- **Tokens** — `--ai-log-info/-warn/-error`, `--ai-done-text`,
  `--text-tertiary`.

## Console Output

- **Purpose** — static block of prompt-prefixed output lines (one command's
  full captured stdout).
- **When to use / not** — a finished command's output. For chrome (title bar,
  traffic-light dots) around it, wrap in `Terminal`.
- **Anatomy** — `p5b-console-output` → `__line` rows, each with an optional
  `__prompt` (`$`) and tone-colored text.
- **Variants** — none; a single block layout, per-line tone is data-driven
  (`ConsoleLine.tone`).
- **Sizes** — single size (fixed `0.8125rem` font-size); no compact-density
  override defined.
- **States** — none; a static block, no interactive states.
- **Keyboard** — none; not focusable.
- **Accessibility** — same color-only tone caveat as ANSI Renderer: `--info/
  -warn/-error/-done` recolor text with no accompanying icon.
- **Content guidelines** — `prompt` is optional per line (only rendered when
  set, e.g. "$") — most output lines omit it; text has no wrapping/
  truncation rule in the CSS.
- **Tokens** — `--surface-sunken`, `--text-terminal`, `--ai-log-info/-warn/
  -error`, `--ai-done-text`, `--text-secondary`.

## Terminal

- **Purpose** — chrome wrapper around `ConsoleOutput`: a title bar with
  traffic-light dots and a session/command title.
- **When to use / not** — presenting a captured CLI session as a recognizable
  terminal window. Not needed for a single inline output line.
- **Anatomy** — `p5b-terminal` → `__bar` (dots + title) and `__body`
  (the wrapped `ConsoleOutput`).
- **Variants** — none; a single chrome layout wrapping any children
  (typically `ConsoleOutput`).
- **Sizes** — single size; no compact-density override defined.
- **States** — none; static chrome, no interactive states.
- **Keyboard** — none; not focusable.
- **Accessibility** — the three traffic-light dots are `aria-hidden="true"`
  (decorative only, not real window controls); the title bar text is the
  only accessible label.
- **Content guidelines** — title is a short session/command label (e.g.
  "productagents — evaluate_initiative"), not the full invoked command
  string.
- **Tokens** — `--surface-sunken`, `--border-subtle`, `--border-default`,
  `--card-radius`, `--text-caption`.

## Copy Output

- **Purpose** — copy-to-clipboard button with a transient "Copied" confirmed
  state (1.5s).
- **When to use / not** — next to any console block a user might want to copy
  verbatim (e.g. an error to paste into a bug report).
- **Anatomy** — `p5b-copy-output` button, icon swaps copy → check on click.
- **Variants** — none; a single button layout.
- **Sizes** — single size; no compact-density override defined.
- **States** — default vs. copied (auto-reverts).
- **Keyboard** — a real `<button>`, so Enter/Space triggers the copy
  natively; no custom key handling.
- **Accessibility** — `aria-label` reflects current state ("Copy output" /
  "Copied").
- **Content guidelines** — visible label text swaps "Copy" ↔ "Copied" (the
  fuller "Copy output"/"Copied" wording is `aria-label`-only); reverts
  automatically after 1.5s.
- **Tokens** — `--surface-raised/-hover`, `--border-subtle`,
  `--radius-control`, `--focus-ring-width/-offset`, `--border-focus`.

## Command History

- **Purpose** — list of prior invocations: command text, timestamp, exit
  status.
- **When to use / not** — a shell-style history panel. Rows are focusable to
  support keyboard re-run/inspect flows even though this gallery doesn't wire
  the action itself.
- **Anatomy** — `p5b-history` ordered list → `__row` (history icon + `__cmd`
  + `__time` + `ExitStatus`).
- **Variants** — none; a single ordered-list row layout.
- **Sizes** — single size; compact density reduces row padding via
  `[data-density="compact"]`.
- **States** — hover (background shifts to `--surface-hover`); `:focus-visible`
  shows an inset ring (`outline-offset: calc(-1 * var(--focus-ring-width))`).
- **Keyboard** — each row is `tabIndex={0}` with a visible focus ring; per
  the When-to-use/not note, Tab reaches every row but nothing happens on
  Enter/Space in this gallery (no `onClick`/`onKeyDown` wired).
- **Accessibility** — `aria-label="command history"` on the list.
- **Content guidelines** — command text is the literal invoked command
  string (can be long, e.g. a full `run evaluate_initiative "..." --evidence
  sample` line) and is truncated with an ellipsis (`text-overflow: ellipsis`),
  not wrapped.
- **Tokens** — `--surface-raised/-hover`, `--border-subtle`, `--text-code`,
  `--text-tertiary`, `--focus-ring-width/-offset`.

## Command Suggestion

- **Purpose** — autocomplete dropdown for a partially-typed command, listing
  matching subcommands with a one-line description.
- **When to use / not** — an in-progress command-line input with live
  suggestions. Not a static reference list — see `CommandBadge` for that.
- **Anatomy** — `p5b-suggest` → `__input` (search icon + typed text + blinking
  cursor) and `__list` (`role="listbox"`) of `__item` (`role="option"`).
- **Variants** — none; a single input+listbox layout.
- **Sizes** — single size; no compact-density override defined.
- **States** — one item marked `aria-selected="true"` (highlighted).
- **Keyboard** — the `listbox`/`option` roles declare the pattern, but no
  `onKeyDown` (arrow-key navigation, Enter-to-select) is wired in this demo —
  `aria-selected` is hardcoded to the "reflect" item, not driven by input.
- **Accessibility** — full listbox/option roles for the dropdown.
- **Content guidelines** — each suggestion pairs the literal subcommand
  (`cmd`) with a short one-line description.
- **Implementation notes** — `__input` is a static `<div>` showing typed text
  and a blinking cursor, not a real `<input>` element — this gallery
  demonstrates the visual only; a functional build needs a genuine text
  input wired to the listbox's keyboard behavior.
- **Tokens** — `--surface-raised/-sunken`, `--border-subtle`, `--text-code`,
  `--text-tertiary`, `--accent`.

## Live Streaming Output

- **Purpose** — single in-progress output line with a blinking terminal
  cursor, for output still being written.
- **When to use / not** — the tail of a running command's stream. Once
  finished, the line becomes a normal `ConsoleOutput` row (no cursor).
- **Anatomy** — `p5b-live-output` (`role="log"`, `aria-live="polite"`) →
  text + `p5b-cursor`.
- **Variants** — none; a single row layout (text + cursor).
- **Sizes** — single size; no compact-density override defined.
- **States** — none exposed as a prop; the cursor always shows while the
  component is mounted — the transition to a finished `ConsoleOutput` row
  (per When-to-use/not) happens by swapping components at the call site.
- **Keyboard** — none; a static, non-interactive display.
- **Accessibility** — `aria-live="polite"` so screen readers announce new
  lines without interrupting; cursor blink respects
  `prefers-reduced-motion` (parked solid).
- **Content guidelines** — text is a single in-progress line (e.g.
  "strategist: synthesizing recommendation from 5 analyst reports…") — no
  prompt/tone styling like `ConsoleOutput`'s lines.
- **Tokens** — `--surface-sunken`, `--text-terminal`, `--text-secondary`.
