"""The pipeline rail — a one-line spine tracing the decision through its stages."""

from textual.widgets import Static

# (key, label) in pipeline order. `analysis` shows a live N/5 counter.
STAGES: list[tuple[str, str]] = [
    ("evidence", "Evidence"),
    ("analysis", "Analysis"),
    ("debate", "Debate"),
    ("strategy", "Strategy"),
    ("judge", "Judge"),
    ("risk", "Risk"),
    ("governance", "Governance"),
]

_HUE = {
    "evidence": "#5eead4",
    "analysis": "#38bdf8",
    "debate": "#fbbf24",
    "strategy": "#34d399",
    "judge": "#a78bfa",
    "risk": "#fb7185",
    "governance": "#c084fc",
}

_GLYPH = {
    "queued": "·",
    "running": "▸",
    "done": "✓",
    "warning": "⚠",
    "failed": "✗",
}


def _segment(key: str, label: str, state: str, analyst_done: int, total: int) -> str:
    glyph = _GLYPH.get(state, "·")
    if key == "analysis":
        label = f"{label} {analyst_done}/{total}"
    if state == "queued":
        return f"[dim]{glyph} {label}[/dim]"
    if state == "failed":
        return f"[b #f43f5e]{glyph} {label}[/]"
    if state == "warning":
        return f"[b #fb923c]{glyph} {label}[/]"
    return f"[b {_HUE[key]}]{glyph} {label}[/]"


def render_rail(
    states: dict[str, str], analyst_done: int, analyst_total: int = 5
) -> str:
    """Render the full rail line from a stage→state map."""
    parts = [
        _segment(key, label, states.get(key, "queued"), analyst_done, analyst_total)
        for key, label in STAGES
    ]
    return "  [dim]→[/dim]  ".join(parts)


class PipelineRail(Static):
    """A live, single-line progress spine for the decision pipeline."""

    def __init__(self) -> None:
        super().__init__(id="pipeline-rail")
        self._states: dict[str, str] = {}
        self._analyst_done = 0
        self.reset()

    def reset(self) -> None:
        self._states = {key: "queued" for key, _ in STAGES}
        self._analyst_done = 0
        self._repaint()

    def set_stage(self, key: str, state: str) -> None:
        if key in self._states:
            self._states[key] = state
            self._repaint()

    def bump_analyst(self) -> None:
        self._analyst_done += 1
        self._repaint()

    def _repaint(self) -> None:
        self.update(render_rail(self._states, self._analyst_done))
