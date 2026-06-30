# Phase 5B — CLI

Terminal chrome and command-output primitives for the `productagents` CLI:
history, autocomplete, streaming output, and ANSI-style status coloring.
Reuses the same "always-dark terminal surface" pattern Phase 4B established
for `StreamingConsole` (`--surface-sunken` regardless of theme, `--ai-log-*`
tones, `--text-terminal`/`--text-code` fonts) — no new tokens. Live gallery:
`styleguide` → Workflow & CLI → 5B.

Icons are inline SVG (`viewBox 0 0 24 24`, `stroke currentColor`,
`stroke-width 1.75`, round caps), defined locally in `Phase5CLI.tsx`.

---

## Command Badge

- **Purpose** — inline monospace chip naming a CLI subcommand (`run`, `sync`,
  `sessions list`, `reflect`).
- **When to use / not** — referencing a command name inline in prose or a UI
  label. Not for the command-history rows themselves (those use
  `p5b-history__cmd`, unboxed, for scanability in a list).
- **Anatomy** — `p5b-cmd-badge`, a `<code>` element.
- **Tokens** — `--surface-sunken`, `--border-subtle`, `--radius-control`,
  `--text-code`.

## Exit Status

- **Purpose** — process exit code indicator: success (0) vs. failure
  (nonzero), icon + label + code.
- **When to use / not** — attached to any completed command invocation (a
  history row, a console block's summary line).
- **Anatomy** — `p5b-exit-status` inline group: check/x icon + "exit N" text.
- **States** — `data-ok="true"` (success, `--ai-done` family) vs. the default
  failure state (`--ai-failed`).
- **Accessibility** — icon + text together, never color alone.
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
- **Tokens** — `--ai-log-info/-warn/-error`, `--ai-done-text`,
  `--text-tertiary`.

## Console Output

- **Purpose** — static block of prompt-prefixed output lines (one command's
  full captured stdout).
- **When to use / not** — a finished command's output. For chrome (title bar,
  traffic-light dots) around it, wrap in `Terminal`.
- **Anatomy** — `p5b-console-output` → `__line` rows, each with an optional
  `__prompt` (`$`) and tone-colored text.
- **Tokens** — `--surface-sunken`, `--text-terminal`, `--ai-log-info/-warn/
  -error`, `--ai-done-text`, `--text-secondary`.

## Terminal

- **Purpose** — chrome wrapper around `ConsoleOutput`: a title bar with
  traffic-light dots and a session/command title.
- **When to use / not** — presenting a captured CLI session as a recognizable
  terminal window. Not needed for a single inline output line.
- **Anatomy** — `p5b-terminal` → `__bar` (dots + title) and `__body`
  (the wrapped `ConsoleOutput`).
- **Tokens** — `--surface-sunken`, `--border-subtle`, `--border-default`,
  `--card-radius`, `--text-caption`.

## Copy Output

- **Purpose** — copy-to-clipboard button with a transient "Copied" confirmed
  state (1.5s).
- **When to use / not** — next to any console block a user might want to copy
  verbatim (e.g. an error to paste into a bug report).
- **Anatomy** — `p5b-copy-output` button, icon swaps copy → check on click.
- **States** — default vs. copied (auto-reverts).
- **Accessibility** — `aria-label` reflects current state ("Copy output" /
  "Copied").
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
- **Keyboard** — each row is `tabIndex={0}` with a visible focus ring.
- **Tokens** — `--surface-raised/-hover`, `--border-subtle`, `--text-code`,
  `--text-tertiary`, `--focus-ring-width/-offset`.

## Command Suggestion

- **Purpose** — autocomplete dropdown for a partially-typed command, listing
  matching subcommands with a one-line description.
- **When to use / not** — an in-progress command-line input with live
  suggestions. Not a static reference list — see `CommandBadge` for that.
- **Anatomy** — `p5b-suggest` → `__input` (search icon + typed text + blinking
  cursor) and `__list` (`role="listbox"`) of `__item` (`role="option"`).
- **States** — one item marked `aria-selected="true"` (highlighted).
- **Accessibility** — full listbox/option roles for the dropdown.
- **Tokens** — `--surface-raised/-sunken`, `--border-subtle`, `--text-code`,
  `--text-tertiary`, `--accent`.

## Live Streaming Output

- **Purpose** — single in-progress output line with a blinking terminal
  cursor, for output still being written.
- **When to use / not** — the tail of a running command's stream. Once
  finished, the line becomes a normal `ConsoleOutput` row (no cursor).
- **Anatomy** — `p5b-live-output` (`role="log"`, `aria-live="polite"`) →
  text + `p5b-cursor`.
- **Accessibility** — `aria-live="polite"` so screen readers announce new
  lines without interrupting; cursor blink respects
  `prefers-reduced-motion` (parked solid).
- **Tokens** — `--surface-sunken`, `--text-terminal`, `--text-secondary`.
