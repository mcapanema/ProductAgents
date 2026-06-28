# agents/ — graph nodes + orchestration

The graph nodes (analysts, debate, strategist, judge, risk, governance, recall) and
the orchestration layer that wires them together and normalizes stream output for the UI.

## Prompt Registry

Node prompts are `string.Template` assets resolved by `prompts.py::PromptStore`. On
`get(name)` / `render(name, **values)` the store first checks the active workspace
override directory (`PRODUCTAGENTS_PROMPTS_DIR/<name>/NNNN.txt`, highest number
wins); if no override exists it falls back to the bundled default loaded via
`importlib.resources` from `prompts/defaults/<name>.txt`. Version 0 always means
the bundled default.

**Nodes render via `ctx.prompts.render(name, **values)`** — the `AgentContext` carries
a `PromptStore` instance wired to the active workspace. For the out-of-graph `reflect`
agent (which has no `AgentContext`) use `prompts or PromptStore()` as a fallback.

The `_format_*` helpers in `_format.py` stay in code — they produce the keyword
substitution values that `render()` passes to `string.Template.substitute`. Using
`substitute` (not `str.format`) means untrusted `{` / `$` characters in evidence
text are inserted literally without triggering template expansion.

## Progress streaming contract

Nodes emit progress events to the runner via `agents/_stream.get_writer()`. The progress
dict itself is built via `agents/stream_events.py` helpers (`emit_status`, `emit_error`,
`emit_payload`, `emit_fatal`) — these are the **single source of truth** for the wire
keys the runner parses. Always use the helpers rather than raw dict literals to keep
the wire format stable and auditable.
