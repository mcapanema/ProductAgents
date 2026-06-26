# tui/ — the Textual layer

The only layer that knows about the screen. It consumes the runner's event
dataclasses and knows nothing about LangGraph. `main()` (in `app.py`) is the
`productagents` entry point.

## Files

| File | Role |
| --- | --- |
| `app.py` | `ProductAgentsApp` + `main()`. Builds the model/graph once (`_build_app`), runs a decision in a `@work(exclusive=True)` worker, and updates one panel per event. `app.tcss` is the stylesheet. |
| `approval.py` | `ApprovalScreen` (`ModalScreen[HumanDecision]`). Shows the advisory verdict; the button id (`approve`/`reject`/`request_analysis`) becomes the `HumanDecision.verdict`. |
| `reflection.py` | `ReflectionScreen`. Pick a past decision, describe what happened, and record an `OutcomeRecord` via the injected reflector — drives the out-of-graph reflection loop (bound to `ctrl+r`). |
| `home_screen.py` | `HomeScreen` (`Screen`). Landing menu shown on launch; buttons delegate to `app.open_setup()` / `app.start_decision()` / `app.exit()`. `refresh_status()` updates the readiness line and enables/disables the run button. Now also shows a connector-config line and a "Sync data sources" button that calls `app.sync_sources()`. |
| `setup_screen.py` | `SetupScreen` (`ModalScreen[bool]`). Collects model/provider/key, validates, and writes them via the injected `writer` (`setup.write_env`). Dismisses `True` on save, `False` on cancel. |
| `rail.py` | `PipelineRail` (`#pipeline-rail`) — the one-line spine tracing the run through the 7 pipeline stages. `render_rail()` is pure; the app advances it from the same handlers that update the panels. |
| `_format.py` | Pure Rich-markup render helpers (recommendation, judgment, debate turn, risk line, governance, recall body, `confidence_meter`). The only `.py` place markup colors live. Unit-tested in `tests/test_tui_format.py`. |

## The event loop

`app._run` iterates `self._runner(...)` and dispatches by event type:
`ProgressEvent`/`NodeCompleteEvent` → analyst panels (gated by `_PANELS`),
`DebateTurnEvent` → debate scroll, `RiskAssessmentEvent` → risk scroll,
`GovernanceVerdictEvent`/`FinalVerdictEvent` → governance panel, `JudgmentEvent`
→ quality-judge panel, `RecallEvent` → lessons panel, `RecommendationEvent` →
strategist panel (rendered live each time the strategist produces a recommendation,
including during judge-retry revisions, before `FinishedEvent` arrives),
`FinishedEvent` → finalise the recommendation panel and persist a `DecisionRecord`
(now including `judgment`). Any new event type needs a branch here **and** (usually) a
`_PANELS` entry, or it is silently dropped.

## Dependency-injection seams

`ProductAgentsApp.__init__` takes every external collaborator as a parameter so
the app is testable headless (see `tests/test_tui.py`):

- `runner` — normally `make_decision_runner(model)` (opens a per-run `AgentContext` session and builds the graph per run); call signature is unchanged so tests still inject a fake runner.
- `collector` — `collect_evidence` (resolves the evidence-source input per run).
- `recorder` — **async** `make_recorder()` closure (persists a `DecisionRecord` to the DB via `LearningService`). Default `None`; `_build_app` injects the DB-backed closure.
- `reader` — **async** `make_decision_reader()` closure (reads past decisions for the reflection picker). Default `None`; `_build_app` injects the DB-backed closure.
- `outcome_recorder` — **async** `make_outcome_recorder()` closure (persists an `OutcomeRecord`). Default `None`; `_build_app` injects the DB-backed closure.
- `reflector` — `partial(reflect, model=model)`; `None` disables `ctrl+r`.
- `connector_syncer` — async `run_connector_sync` (loads YAML config, syncs
  enabled connectors into the canonical store, persists cursors). Injectable for
  headless tests.
- `connector_planner` — `static_connector_plan` (fail-fast config preflight, no
  I/O); the home screen renders `describe_plan(...)` of its result.

The `outcome_reader` seam and the `portfolio`/`outcomes` run-seeding are **removed** — lessons are now retrieved inside the graph by the `recall` node via `AgentContext.learning` (the `LearningService`). JSONL helpers in `productagents.memory` remain available for export/audit only.

`_record` is `async`; it is `await`ed in the `_run` worker (after `FinishedEvent`) and in `_handle_degraded` (on the "decide" path). `ReflectionScreen` loads decisions via a `@work(exclusive=True)` worker (`_load_decisions`) so the async reader is safe from `on_mount`.

## HITL pause

On a governance `__interrupt__`, `run_decision` calls the app's `_ask_human`,
which `push_screen_wait(ApprovalScreen(...))` and returns the `HumanDecision`
that resumes the graph; a `FinalVerdictEvent` then updates the governance panel.

## First-run menu & setup

`on_mount` pushes `HomeScreen` (skipped when `show_home=False`, used by the
decision/approval/reflection tests). If `config_checker()` reports the app isn't
ready, `open_setup()` pushes `SetupScreen` on top. A successful save calls the
injected `rebuild()` to rebuild the runner/reflector with the new config, then
refreshes the home status. "Run a decision" pops `HomeScreen` to reveal the base
decision UI; `ctrl+h` re-opens the menu. New DI seams on `ProductAgentsApp`:
`config_checker` (default `setup.check_config`), `env_writer` (default
`setup.write_env`), `rebuild` (default `None`; `main` injects the real builder),
and `show_home`.

## Testing

Drive the app with Textual's `run_test()` pilot and fakes for every seam; assert
on panel text. The headless tests never start a real model or graph.
