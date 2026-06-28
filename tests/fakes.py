"""Test doubles for offline agent/graph testing."""

from uuid import uuid4

from productagents.agents.evidence import collect_evidence
from productagents.app.setup import ConfigStatus
from productagents.platform import events as ev
from productagents.platform.decision_service import DecisionService
from productagents.platform.session import Session


class FakeDecisionService:
    """Test double for ``platform.DecisionService``.

    Wraps a ``runner`` (the old ``run_decision`` async-gen contract:
    ``runner(initiative, evidence, *, approver)`` yielding runner events),
    resolves the evidence spec, translates runner events into the platform's
    event vocabulary, and records on a healthy finish — mirroring the real
    service so TUI tests can keep building runners exactly as before.
    """

    def __init__(
        self, runner, *, recorder=None, evidence=None, collector=collect_evidence
    ):
        self._runner = runner
        self._recorder = recorder
        self._evidence = evidence
        self._collector = collector
        # Borrow the real service's runner→platform translation + record helpers
        # so the mapping stays single-sourced.
        self._svc = DecisionService(lambda: None, recorder=recorder)

    def start_session(self, initiative, evidence_spec, *, approver=None):
        if evidence_spec:
            evidence = self._collector(evidence_spec)
        elif self._evidence is not None:
            evidence = self._evidence
        else:
            evidence = self._collector("sample")
        session = Session(id=uuid4().hex, workflow="evaluate_initiative")
        return session, self._stream(session, initiative, evidence, approver)

    async def _stream(self, session, initiative, evidence, approver):
        from productagents.agents import runner as rn

        seq = 0
        runner_approver = self._wrap_approver(session, approver)
        async for r in self._runner(initiative, evidence, approver=runner_approver):
            make = self._svc._translate(session, r)
            if make is not None:
                yield make(seq)
                seq += 1
            if isinstance(r, rn.RunAbortedEvent):
                return
            if isinstance(r, rn.FinishedEvent):
                await self._svc._record(session, initiative, evidence, r)

    def _wrap_approver(self, session, approver):
        if approver is None:
            return None

        async def runner_approver(advisory):
            return await approver(
                ev.ApprovalRequested(
                    session_id=session.id,
                    seq=-1,
                    advisory_verdict=advisory.verdict if advisory else "approve",
                    advisory_rationale=advisory.rationale if advisory else "",
                )
            )

        return runner_approver


def ready_status() -> ConfigStatus:
    """A ConfigStatus that reports the app is fully configured."""
    return ConfigStatus(
        model="anthropic:claude-sonnet-4-6",
        provider="anthropic",
        key_var="ANTHROPIC_API_KEY",
        key_present=True,
    )


class _FakeStructured:
    def __init__(self, result):
        self._result = result

    async def ainvoke(self, _input):
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class _FakeSequenced:
    """Returns items from a list in order; repeats the last item once exhausted."""

    def __init__(self, sequence):
        self._sequence = list(sequence)
        self._index = 0

    async def ainvoke(self, _input):
        item = self._sequence[min(self._index, len(self._sequence) - 1)]
        self._index += 1
        if isinstance(item, Exception):
            raise item
        return item


class FakeChatModel:
    """Stands in for a LangChain chat model in tests.

    `results` maps a Pydantic schema class to the instance that
    `with_structured_output(schema).ainvoke(...)` should return. If the mapped
    value is an Exception instance, `ainvoke` raises it instead.

    To vary the response across multiple calls to the same schema, map the schema
    to a *list* of values. The first call returns `results[0]`, the second returns
    `results[1]`, etc. Once exhausted, the last value is repeated.

    Example (judge fails once, then passes)::

        model = FakeChatModel({
            JudgeFinding: [
                JudgeFinding(evidence_grounding_score=0.3, ...),  # fail
                JudgeFinding(evidence_grounding_score=0.9, ...),  # pass
            ],
        })
    """

    def __init__(self, results: dict):
        self._results = results
        # Pre-build _FakeSequenced instances so the call index persists across
        # multiple with_structured_output() calls for the same schema.
        self._structured: dict = {
            schema: _FakeSequenced(value)
            if isinstance(value, list)
            else _FakeStructured(value)
            for schema, value in results.items()
        }

    def with_structured_output(self, schema, **_kwargs):
        if schema not in self._structured:
            raise KeyError(f"FakeChatModel has no result for schema {schema!r}")
        return self._structured[schema]


def fake_context(model, *, feedback=None):
    """Wrap a (fake) model into an AgentContext for node/graph tests.

    `feedback` defaults to the context's own `_NullFeedback` (empty store), so
    analyst tests exercise scenario evidence unless they opt into a store.
    """
    from productagents.agents.context import AgentContext

    if feedback is None:
        return AgentContext(model=model)
    return AgentContext(model=model, feedback=feedback)
