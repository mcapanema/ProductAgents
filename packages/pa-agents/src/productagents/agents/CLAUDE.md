# agents/ — graph nodes + orchestration

The graph nodes (analysts, debate, strategist, judge, risk, governance, recall) and
the orchestration layer that wires them together and normalizes stream output for the UI.

## Progress streaming contract

Nodes emit progress events to the runner via `agents/_stream.get_writer()`. The progress
dict itself is built via `agents/stream_events.py` helpers (`emit_status`, `emit_error`,
`emit_payload`, `emit_fatal`) — these are the **single source of truth** for the wire
keys the runner parses. Always use the helpers rather than raw dict literals to keep
the wire format stable and auditable.
