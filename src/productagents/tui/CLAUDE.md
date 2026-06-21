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

## The event loop

`app._run` iterates `self._runner(...)` and dispatches by event type:
`ProgressEvent`/`NodeCompleteEvent` → analyst panels (gated by `_PANELS`),
`DebateTurnEvent` → debate scroll, `RiskAssessmentEvent` → risk scroll,
`GovernanceVerdictEvent`/`FinalVerdictEvent` → governance panel, `RecallEvent` →
lessons panel, `FinishedEvent` → render the recommendation and persist a
`DecisionRecord`. Any new event type needs a branch here **and** (usually) a
`_PANELS` entry, or it is silently dropped.

## Dependency-injection seams

`ProductAgentsApp.__init__` takes every external collaborator as a parameter so
the app is testable headless (see `tests/test_tui.py`):

- `runner` — normally `partial(run_decision, graph)`.
- `collector` — `collect_evidence` (resolves the evidence-source input per run).
- `recorder` / `reader` — `record_decision` / `read_decisions` (decision log).
- `outcome_reader` / `outcome_recorder` — `read_outcomes` / `record_outcome`.
- `reflector` — `partial(reflect, model=model)`; `None` disables `ctrl+r`.

`portfolio` and `outcomes` are read from the logs **here** and passed into
`run_decision`, keeping the graph nodes filesystem-free.

## HITL pause

On a governance `__interrupt__`, `run_decision` calls the app's `_ask_human`,
which `push_screen_wait(ApprovalScreen(...))` and returns the `HumanDecision`
that resumes the graph; a `FinalVerdictEvent` then updates the governance panel.

## Testing

Drive the app with Textual's `run_test()` pilot and fakes for every seam; assert
on panel text. The headless tests never start a real model or graph.
