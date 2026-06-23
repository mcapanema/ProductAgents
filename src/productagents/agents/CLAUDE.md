# agents/ — the node layer

One graph node per file. A node is an `async def *_node(state: dict, model) ->
dict` that reads from `state`, optionally issues **one** structured LLM call, and
returns the partial `GraphState` it owns. Nodes are pure functions of their
arguments — the model is injected (never `get_model()` here), and prior decisions
arrive via `state`, never the filesystem.

## The four rules

1. **Degrade, never crash.** Wrap the LLM call in `try/except Exception` with
   `# noqa: BLE001` and return a fallback (`failed=True` report, placeholder
   debate turn, `"error"`/`"unknown"` sentinel, or zero-confidence rec). One
   failure must not abort the graph.
2. **Stream through `get_writer()`.** Import from `agents._stream`, not
   `langgraph.config` — the helper returns a no-op writer when a node is called
   directly in a unit test. Emit `{"node": id, "status": "…"}` for progress and
   richer payloads (`turn`, `assessment`, `verdict`, `final_verdict`) for live
   rendering; `runner.py` translates these into events.
3. **Structured output only, via `invoke_structured`.** Call
   `invoke_structured(model, Schema, prompt, node=NODE_ID)` (from `agents._llm_call`)
   rather than `model.with_structured_output(Schema).ainvoke(...)` directly — it
   centralizes logging and converts an empty (`None`) result into a clear
   `StructuredOutputError`. `Schema` is an LLM-output model from `schemas.py`.
   Assemble the enriched record yourself.
   On a fatal failure (rate limit, bad key, no tool calling) the wrapper also
   emits a `fatal` stream marker; `runner.py` turns that into a `RunAbortedEvent`
   and stops the run. Nodes still catch and degrade exactly as before.
4. **Return only your slice of `GraphState`.** e.g. `{"reports": [report]}`,
   `{"debate": turns}`, `{"recommendation": rec}`.

## Files

| File | Node / role |
| --- | --- |
| `_analyst.py` | `run_analyst(...)` — shared executor for the five analysts (progress events + structured call + graceful degradation). Not a node itself. |
| `_format.py` | `format_reports_brief`, `format_transcript` — shared prompt formatters used by debate/risk (and strategist for the transcript). |
| `_llm_call.py` | `invoke_structured(model, schema, prompt, *, node)` — the one wrapper every node's structured call routes through. Logs the call + full tracebacks, classifies provider exceptions via `productagents.agents.llm_errors.classify_provider_error` into a friendly `ProviderError`, raises `StructuredOutputError` when the model returns `None`, and on a **fatal** category emits a `{"fatal": True}` stream marker so `runner.py` can stop the run. Not a node. |
| `_stream.py` | `get_writer()` — active stream writer or a no-op outside a graph run. |
| `customer_research.py`, `product_analytics.py`, `market.py`, `business.py`, `technical.py` | The five parallel analysts. Each is a thin delegate: module constants + a `_prompt(initiative, evidence)` + a `*_node` that calls `run_analyst`. |
| `debate.py` | Advocate-vs-Skeptic loop, `get_debate_rounds()` rounds (env `PRODUCTAGENTS_DEBATE_ROUNDS`, default 2). Emits each turn. |
| `recall.py` | Model-free; selects lessons from past decisions via `memory.select_relevant_lessons`. Runs in parallel from `START`. |
| `strategist.py` | Synthesizes reports + debate + recalled lessons into a `Recommendation`. On revision runs, appends the judge's critique via `_format_critique`. |
| `judge.py` | LLM-as-Judge gate on the recommendation. Scores evidence grounding + rationale coherence (`JudgeFinding`), computes pass/fail from `get_judge_threshold()` (env `PRODUCTAGENTS_JUDGE_THRESHOLD`, default 0.7), and returns a `JudgeVerdict` + incremented `judge_attempts`. The graph loops it back to the strategist up to `get_judge_max_retries()` times (env `PRODUCTAGENTS_JUDGE_MAX_RETRIES`, default 1; 0 = score-only). |
| `risk.py` | Five fixed reviewers (`REVIEWERS`), each a structured `RiskFinding`. Emits each assessment. |
| `governance.py` | Portfolio Manager advisory `GovernanceVerdict`, weighed against the recent portfolio window. |
| `human_approval.py` | HITL only. `interrupt()` pauses for a human; the resumed `HumanDecision` becomes the binding verdict (`decided_by="human"`, advisory preserved). |
| `reflection.py` | **Out of graph.** `reflect(decision, note, model)` runs after the fact (triggered from the TUI reflection screen) to produce an `OutcomeRecord` — the capture half of Outcome Learning. |

## Adding an analyst

Copy any analyst file, change `ANALYST_ID` / `ROLE` / `_START_STATUS`, write the
`_prompt`, and let `run_analyst` do the rest. Then register it in `graph.py`
(node + `START`→node and node→`debate` edges) and add a `_PANELS` entry in
`tui/app.py`.

## Testing

Call a node directly with a `FakeChatModel` (`tests/fakes.py`) mapping the
schema class → the instance (or `Exception`) the call should return. No graph,
no event loop boilerplate (`asyncio_mode = "auto"`). See `tests/CLAUDE.md`.
