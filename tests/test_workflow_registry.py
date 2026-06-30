"""Entry-point discovery of installed workflows (mirrors test_connector_registry)."""

from importlib.metadata import EntryPoint

from productagents.platform import workflow_registry as reg
from productagents.platform.workflow import Workflow, build_evaluate_initiative
from tests.fakes import FakeChatModel


def _dummy_builder(
    model, *, recorder=None, human_in_the_loop=False, persist_events=True
) -> Workflow:
    def _start(*a, **k):
        return ("", None)  # type: ignore[return-value]

    return Workflow(name="dummy", title="Dummy", description="d", start=_start)  # type: ignore[arg-type]


def test_discover_maps_name_to_builder(monkeypatch):
    ep = EntryPoint(
        name="dummy",
        value="tests.test_workflow_registry:_dummy_builder",
        group="productagents.workflows",
    )
    monkeypatch.setattr(reg, "entry_points", lambda group: [ep])
    assert reg.discover() == {"dummy": _dummy_builder}


def test_discover_empty_when_no_entry_points(monkeypatch):
    monkeypatch.setattr(reg, "entry_points", lambda group: [])
    assert reg.discover() == {}


def test_discover_skips_broken_entry_point(monkeypatch):
    bad = EntryPoint(
        name="broken",
        value="tests.test_workflow_registry:does_not_exist",
        group="productagents.workflows",
    )
    monkeypatch.setattr(reg, "entry_points", lambda group: [bad])
    assert reg.discover() == {}  # load() failure is swallowed, not raised


def test_build_evaluate_initiative_returns_named_workflow():
    wf = build_evaluate_initiative(FakeChatModel({}), persist_events=False)
    assert wf.name == "evaluate_initiative"
    assert wf.title == "Evaluate Initiative"
    assert callable(wf.start)


def test_discover_finds_real_evaluate_initiative():
    found = reg.discover()
    assert found.get("evaluate_initiative") is build_evaluate_initiative
