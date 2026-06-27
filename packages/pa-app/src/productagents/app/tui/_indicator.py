"""The panel state-indicator state machine, split out of the App.

Owns each panel's border-title icon (idle/waiting/running/done/failed/warning)
and the rotating spinner for running panels. Holds a reference back to the host
App only to query widgets and schedule the spinner timer; all icon/lifecycle
logic lives here so app.py is about event handling, not painting.
"""

from textual.css.query import NoMatches

from productagents.app.tui._constants import SPINNER_FRAMES, STATE_ICON, TITLES

_LIFECYCLE = {
    "idle": "-idle",
    "waiting": "-idle",
    "running": "-active",
    "done": "-done",
    "failed": "-done",
    "warning": "-done",
}


class PanelIndicator:
    def __init__(self, app) -> None:
        self._app = app
        self._spinning: set[str] = set()
        self._frame: int = 0
        self._timer = None

    def set_state(self, widget_id: str, state: str) -> None:
        try:
            widget = self._app.query_one(f"#{widget_id}")
        except NoMatches:
            return
        widget.remove_class("failed", "warning", "-idle", "-active", "-done")
        lifecycle = _LIFECYCLE.get(state)
        if lifecycle:
            widget.add_class(lifecycle)
        if state == "failed":
            widget.add_class("failed")
        elif state == "warning":
            widget.add_class("warning")
        if state == "running":
            self._spinning.add(widget_id)
            self._ensure_timer()
            self._paint(widget_id, SPINNER_FRAMES[self._frame])
        else:
            self._spinning.discard(widget_id)
            self._paint(widget_id, STATE_ICON[state])

    def _paint(self, widget_id: str, icon: str) -> None:
        try:
            widget = self._app.query_one(f"#{widget_id}")
        except NoMatches:
            return
        base = TITLES.get(widget_id, widget_id)
        widget.border_title = f"{icon} {base}"

    def _ensure_timer(self) -> None:
        if self._timer is None:
            self._timer = self._app.set_interval(0.12, self._advance)

    def _advance(self) -> None:
        if not self._spinning:
            return
        self._frame = (self._frame + 1) % len(SPINNER_FRAMES)
        frame = SPINNER_FRAMES[self._frame]
        for widget_id in self._spinning:
            self._paint(widget_id, frame)
