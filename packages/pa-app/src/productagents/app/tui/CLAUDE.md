# tui/ — the Textual layer

The only layer that knows about the screen. It is a **thin client of the
`productagents.platform` Application Services**: it imports only the
`platform.*` and `core.*` namespaces — never the `agents` package. It consumes
the platform's event vocabulary (`platform.events`) and knows nothing about
LangGraph or the runner. `main()` (in `app.py`) is the `productagents` entry
point.

## Files

| File | Role |
| --- | --- |
| `app.py` | `ProductAgentsApp` + `main()`. Builds the model + a `WorkflowService` once (`_build_app`), runs a decision session via `run("evaluate_initiative", …)` in a `@work(exclusive=True)` worker, and updates one panel per platform event. `app.tcss` is the stylesheet. |
| `approval.py` | `ApprovalScreen` (`ModalScreen[HumanDecision]`). Shows the advisory verdict; the button id (`approve`/`reject`/`request_analysis`) becomes the `HumanDecision.verdict`. |
| `reflection.py` | `ReflectionScreen`. Pick a past decision, describe what happened, and record an `OutcomeRecord` via the injected reflector — drives the out-of-graph reflection loop (bound to `ctrl+r`). |
| `home_screen.py` | `HomeScreen` (`Screen`). Landing menu shown on launch; buttons delegate to `app.open_setup()` / `app.start_decision()` / `app.exit()`. `refresh_status()` updates the readiness line and enables/disables the run button. Now also shows a connector-config line, a "Sync data sources" button (`app.sync_sources()`), and a **"Check connector health"** button (`#home-health` → `app.check_health()`) that calls `sync.check_connector_health()` and renders the per-connector health result on the connectors line. |
| `setup_screen.py` | `SetupScreen` (`ModalScreen[bool]`). Collects model/provider/key, validates, and writes them via the injected `writer` (`setup.write_env`). Dismisses `True` on save, `False` on cancel. |
| `rail.py` | `PipelineRail` (`#pipeline-rail`) — the one-line spine tracing the run through the 7 pipeline stages. `render_rail()` is pure; the app advances it from the same handlers that update the panels. |
| `_format.py` | Pure Rich-markup render helpers (recommendation, judgment, debate turn, risk line, governance, recall body, `confidence_meter`). The only `.py` place markup colors live. Unit-tested in `tests/test_tui_format.py`. |
| `_constants.py` | Layout/theme tables (TITLES, PANELS, STATE_ICON, SPINNER_FRAMES, WAITING_AT_START, ANALYST_IDS, WIDGET_FOR_NODE, THEME), split out of `app.py`. |
| `_indicator.py` | `PanelIndicator` — the panel state-icon + spinner state machine (set_state/_paint/_advance), split out of `app.py`; `app._set_state` delegates to it. |

## The event loop

`app._run` calls `self._workflow_service.run("evaluate_initiative", initiative, evidence_spec,
approver=self._ask_human)` and iterates the returned `AsyncIterator[ev.Event]`,
dispatching by **platform** event type (`platform.events`):
`NodeProgress`/`AnalystCompleted` → analyst panels (gated by `_PANELS`),
`DebateTurnEmitted` → debate scroll, `RiskAssessed` → risk scroll,
`GovernanceAdvised`/`FinalVerdict` → governance panel, `Judged` → quality-judge
panel, `LessonsRecalled` → lessons panel, `Recommended` → strategist panel
(rendered live each time the strategist produces a recommendation, including during
judge-retry revisions, before `SessionFinished` arrives), `SessionFinished` →
finalise the recommendation panel (the **DecisionService already recorded** a
healthy run — the TUI no longer records it), `SessionFailed` → error banner +
degraded screen. Any new event type needs a branch here **and** (usually) a
`_PANELS` entry. The panel-routing tables are unchanged — only the event *types*
they key on moved from the runner's dataclasses to the platform vocabulary.

## Dependency-injection seams

`ProductAgentsApp.__init__` takes every external collaborator as a parameter so
the app is testable headless (see `tests/test_tui.py`):

- `workflow_service` — normally `WorkflowService.for_model(model, recorder=…, human_in_the_loop=True)` (wraps a `DecisionService` behind the registered `evaluate_initiative` workflow). The TUI calls `run("evaluate_initiative", initiative, evidence_spec, *, approver) -> (Session, AsyncIterator[ev.Event])`. Tests inject `fake_workflow_service(...)` (in `tests/fakes.py`), which wraps a `FakeDecisionService` in a real `WorkflowService`.
- `collector` — `collect_evidence` (from `platform.evidence`; resolves the evidence-source input for the **provenance panel**; the spec string is passed to `start_session`, which resolves it again internally).
- `recorder` — **async** `make_recorder()` closure (persists a `DecisionRecord`). Used **only on the degraded "decide" path** now (the DecisionService records healthy runs); default `None`; `_build_app` injects the DB-backed closure into both the service and the app.
- `reader` — **async** `make_decision_reader()` closure (reads past decisions for the reflection picker). Default `None`; `_build_app` injects the DB-backed closure.
- `outcome_recorder` — **async** `make_outcome_recorder()` closure (persists an `OutcomeRecord`). Default `None`; `_build_app` injects the DB-backed closure.
- `reflector` — `partial(reflect, model=model)`; `None` disables `ctrl+r`.
- `connector_syncer` — async `run_connector_sync` (loads YAML config, syncs
  enabled connectors into the canonical store, persists cursors). Injectable for
  headless tests.
- `connector_health_checker` — async `check_connector_health` (DB-free probe of
  each enabled connector's `health_check()` in a `connector.health` span; returns
  a `HealthReport`). Injectable for headless tests; the home-menu button binds to it.
- `connector_planner` — `static_connector_plan` (fail-fast config preflight, no
  I/O); the home screen renders `describe_plan(...)` of its result.

The `outcome_reader` seam and the `portfolio`/`outcomes` run-seeding are **removed** — lessons are now retrieved inside the graph by the `recall` node via `AgentContext.learning` (the `LearningService`). JSONL helpers in `productagents.memory` remain available for export/audit only.

`_record` is `async` and now runs **only** on the degraded "decide" path inside
`_handle_degraded` (a healthy run is recorded by the DecisionService). It builds
a `DecisionRecord` from `core.models` only — no `agents`/`memory` import.
`ReflectionScreen` loads decisions via a `@work(exclusive=True)` worker
(`_load_decisions`) so the async reader is safe from `on_mount`.

## HITL pause

On a HITL run the DecisionService calls the app's `_ask_human` with an
`ev.ApprovalRequested` (carrying `.advisory_verdict` / `.advisory_rationale`);
`_ask_human` wraps those into a `GovernanceVerdict` for `ApprovalScreen`,
`push_screen_wait`s it, and returns the `HumanDecision` that resumes the run.
An `ev.FinalVerdict` then updates the governance panel.

## First-run menu & setup

`on_mount` pushes `HomeScreen` (skipped when `show_home=False`, used by the
decision/approval/reflection tests). If `config_checker()` reports the app isn't
ready, `open_setup()` pushes `SetupScreen` on top. A successful save calls the
injected `rebuild()` to rebuild the workflow_service/reflector with the new config, then
refreshes the home status. "Run a decision" pops `HomeScreen` to reveal the base
decision UI; `ctrl+h` re-opens the menu. New DI seams on `ProductAgentsApp`:
`config_checker` (default `setup.check_config`), `env_writer` (default
`setup.write_env`), `rebuild` (default `None`; `main` injects the real builder),
and `show_home`.

## Testing

Drive the app with Textual's `run_test()` pilot and fakes for every seam; assert
on panel text. The headless tests never start a real model or graph.
