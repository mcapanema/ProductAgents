from productagents.app.tui._indicator import PanelIndicator


class _FakeWidget:
    def __init__(self):
        self.classes: set[str] = set()
        self.border_title = ""

    def remove_class(self, *names):
        self.classes -= set(names)

    def add_class(self, *names):
        self.classes |= set(names)


class _FakeApp:
    """Minimal stand-in: one widget, a no-op interval timer."""

    def __init__(self):
        self.widget = _FakeWidget()

    def query_one(self, _selector):
        return self.widget

    def set_interval(self, _interval, _callback):
        return object()


def test_done_paints_check_icon_and_done_lifecycle():
    app = _FakeApp()
    indicator = PanelIndicator(app)
    indicator.set_state("strategist", "done")
    assert app.widget.border_title.startswith("✓")
    assert "-done" in app.widget.classes


def test_failed_adds_failed_class():
    app = _FakeApp()
    indicator = PanelIndicator(app)
    indicator.set_state("strategist", "failed")
    assert "failed" in app.widget.classes
    assert app.widget.border_title.startswith("✗")


def test_running_registers_a_spinner_and_paints_a_frame():
    app = _FakeApp()
    indicator = PanelIndicator(app)
    indicator.set_state("debate-scroll", "running")
    assert "debate-scroll" in indicator._spinning
    # A running panel shows a spinner frame, not a static icon.
    assert any(app.widget.border_title.startswith(f) for f in "◐◓◑◒")


def test_leaving_running_discards_the_spinner():
    app = _FakeApp()
    indicator = PanelIndicator(app)
    indicator.set_state("debate-scroll", "running")
    indicator.set_state("debate-scroll", "done")
    assert "debate-scroll" not in indicator._spinning
