# ProductAgents

> ProductAgents is a multi-agent framework for product decision-making under uncertainty.

Inspired by organizational decision-making and multi-agent architectures, ProductAgents models how high-performing product organizations evaluate opportunities, challenge assumptions, manage risk, and make strategic decisions.

> The goal is not to build a smarter AI. The goal is to build a smarter decision-making process.

Real organizations don't rely on a single person to decide what to build next. Product decisions emerge from the interaction of customer insights, business constraints, technical realities, market signals, strategic goals, and healthy disagreement between experts. ProductAgents brings those dynamics into a transparent, traceable, and configurable system that turns organizational knowledge into defensible product decisions.

Every recommendation is **evidence-based, fully traceable, open to challenge, risk-assessed, governed through explicit approval, and continuously improved through learning.**

---

## Core Principles

- **Specialization** — Customer insights, business metrics, technical constraints, and market dynamics each provide different signals; they shouldn't be collapsed into a single summary too early.
- **Structured Disagreement** — Healthy organizations challenge their own assumptions. ProductAgents explicitly creates opposing viewpoints and debate loops before deciding.
- **Transparency** — Every decision is explainable. The framework preserves analyst reports, debate transcripts, risk assessments, approval decisions, and outcome reviews.
- **Learning** — Every decision creates data. The system reflects on past recommendations and uses those lessons to improve future ones.

---

## General Architecture

ProductAgents follows a seven-stage pipeline that turns raw evidence into governed, defensible decisions and learns from every outcome. The architecture stays stable while agents, integrations, and workflows are customized per company.

<p align="center">
  <img src="docs/images/general-architecture.png" alt="General Architecture — the seven-stage pipeline: Evidence Collection, Perspective Formation, Structured Disagreement, Decision Proposal, Risk Evaluation, Governance Approval, and Outcome Learning, wrapped by a continuous learning loop." width="900">
</p>

Equivalently, the system is organized into **six configurable layers**, wrapped by an organizational memory that learns whether each decision was right:

1. **Evidence Collection** — gather facts from internal/external systems (analytics, CRM, feedback, support, market intelligence).
2. **Perspective Formation** — generate independent viewpoints (customer, business, technical, strategic) from the evidence.
3. **Structured Disagreement** — opposing agents challenge assumptions and defend positions through debate.
4. **Decision Proposal** — produce a recommendation from evidence and debate outcomes.
5. **Risk Evaluation** — assess delivery, adoption, strategic, financial, and organizational risks.
6. **Governance Approval** — approve, reject, or request additional analysis.

<p align="center">
  <img src="docs/images/six-layers.png" alt="The Six Layers — Evidence Collection, Perspective Formation, Structured Disagreement, Decision Proposal, Risk Evaluation, and Governance Approval, plus the Organizational Memory loop that records decisions, measures outcomes, and feeds lessons back." width="900">
</p>

---

## Agent Architecture

Specialized agents are organized into teams that gather evidence, debate it, propose a call, stress-test risk, and govern the final decision.

<p align="center">
  <img src="docs/images/agent-architecture.png" alt="Agent Architecture — five teams in sequence: the Analyst Team (five parallel analysts), the Research Team (Opportunity Advocate vs. Skeptic), the Product Strategist, the Risk Team (five reviewers), and the Portfolio Manager (Approve / Reject / Request analysis)." width="900">
</p>

### Analyst Team (runs in parallel)

| Analyst | Analyzes | Produces |
|---|---|---|
| **Customer Research** | Interviews, support tickets, feedback, NPS | Pain points, demand signals, evidence summaries |
| **Product Analytics** | Usage, funnels, retention, adoption | Behavioral insights, impact estimates, opportunity sizing |
| **Market** | Competitors, trends, launches, market shifts | Competitive intel, market opportunities, strategic context |
| **Business** | Revenue, costs, company goals, initiatives | Business impact, goal alignment, ROI considerations |
| **Technical** | Architecture, tech debt, dependencies, complexity | Feasibility, technical risks, effort estimates |

### Research Team

Transforms evidence into arguments through multiple rounds of structured debate; the transcript becomes part of the decision record.

- **Opportunity Advocate** — argues *we should build this*, focusing on customer value, business impact, strategic opportunity, and competitive advantage.
- **Opportunity Skeptic** — argues *we should not build this*, focusing on opportunity cost, risk, complexity, and uncertainty.

### Product Strategist

Consumes analyst reports, debate transcripts, and organizational context to produce a recommendation, priority assessment, confidence score, expected outcomes, and decision rationale.

### Risk Team

Before approval, recommendations pass through five specialized reviewers: **Delivery** (execution feasibility), **Adoption** (customer adoption), **Strategic** (goal alignment), **Financial** (economic viability and return), and **Organizational** (capacity and operational constraints).

### Product Portfolio Manager

The final decision authority. It reviews recommendations, weighs portfolio trade-offs, and approves or rejects initiatives. It doesn't ask *"Is this a good idea?"* but rather *"Is this the best use of our limited resources right now?"*

---

## The Secret Weapon: Organizational Memory

Every completed decision becomes part of the organization's collective learning system. Decision records capture the recommendation; later, the framework evaluates how it actually turned out:

```json
// decision
{ "initiative": "...", "recommendation": "...", "confidence": 0.0, "reasoning": "...", "expected_outcomes": [] }
// outcome
{ "actual_outcomes": [], "prediction_accuracy": 0.0, "lessons_learned": [] }
```

This creates a continuous feedback loop. The goal is not simply to remember decisions — it's to remember **whether those decisions were correct**, and apply those lessons to new choices.

---

## Design Goals

Framework-first and organization-agnostic by default · configurable agent ecosystem · transparent reasoning · human-in-the-loop governance · durable decision history · production-ready orchestration · extensible integrations.

## Technology Stack

- **Runtime:** Python 3.14, [uv](https://docs.astral.sh/uv/)
- **Orchestration:** LangGraph (checkpointed graph execution)
- **Models:** provider-agnostic (OpenAI, Anthropic, Google Gemini, OpenRouter, local models)
- **Structured outputs:** strongly typed schemas for critical decisions
- **Persistence:** decision logs, reflection history, organizational memory

## Future Roadmap

Roadmap prioritization · opportunity assessment · product strategy reviews · quarterly planning · feature investment decisions · build vs. buy analysis · product portfolio management · go-to-market readiness reviews.

---

## Getting Started

The repository currently implements an end-to-end **slice** of the architecture above: five analysts evaluate evidence in parallel, an Advocate and a Skeptic debate the initiative, a strategist produces a recommendation, an LLM-as-Judge quality gate scores it (looping back for revision if it doesn't pass), a five-reviewer Risk Team assesses it, and a Portfolio Manager produces an advisory verdict — then a human makes the binding call (approve / reject / request analysis) in the TUI. Every stage runs live and is saved (with full transcript, judge verdict, risk assessments, and human decision) to the organizational-memory DB (`DecisionStore`).

### Setup

```bash
uv sync
```

### Configure a model

Model selection is provider-agnostic (defaults to `anthropic:claude-sonnet-4-6`). The easiest way is to copy the template — `.env` is loaded automatically on startup and is git-ignored:

```bash
cp .env.example .env   # then edit .env and set your provider API key
```

Variables exported in your shell take precedence over `.env`. To use another provider, set both the model and provider:

```bash
export PRODUCTAGENTS_MODEL="gpt-5.5"
export PRODUCTAGENTS_MODEL_PROVIDER="openai"
export OPENAI_API_KEY="sk-..."
```

**OpenRouter free models** — [OpenRouter](https://openrouter.ai) exposes many models behind one key. Use an `openrouter:`-prefixed id (the prefix selects the provider, and a `:free` suffix is preserved):

```bash
export PRODUCTAGENTS_MODEL="openrouter:deepseek/deepseek-chat-v3-0324:free"
export OPENROUTER_API_KEY="sk-or-..."
```

> **Pick a model that supports tool/function calling.** Every stage uses structured output, so a model without tool support falls back to placeholder results rather than failing loudly. Known-good free options: `deepseek/deepseek-chat-v3-0324:free`, `meta-llama/llama-3.3-70b-instruct:free`, `google/gemini-2.0-flash-exp:free`. Expect free-tier rate limits.
>
> Free OpenRouter models are rate-limited and frequently return transient "Provider returned error" responses under load. `PRODUCTAGENTS_MAX_RETRIES` (default 6) retries these with backoff; if a model hits a hard daily cap, switch to a keyed/paid model.

### Tuning (optional)

```bash
export PRODUCTAGENTS_DEBATE_ROUNDS=2     # each round = one advocate argument + one skeptic rebuttal
export PRODUCTAGENTS_JUDGE_THRESHOLD=0.7 # min score (0-1) for evidence grounding & rationale coherence
export PRODUCTAGENTS_JUDGE_MAX_RETRIES=1 # times the judge can loop back to the strategist; 0 = score-only
export PRODUCTAGENTS_MAX_RETRIES=6      # retry budget (with backoff) for transient provider errors
```

### Connecting data sources

ProductAgents syncs external systems into its local canonical store *before* a
decision runs (no network calls happen during agent execution). Connectors are
configured in a YAML file — `connectors.yaml` by default, or the path in
`PRODUCTAGENTS_CONNECTORS_FILE`. Copy `connectors.yaml.example` to start:

```yaml
connectors:
  github:
    enabled: true
    owner: your-org
    repo: your-repo
    token_env: GITHUB_TOKEN   # token read from $GITHUB_TOKEN, never inlined
```

Each connector block is validated against that connector's typed schema at
startup; a missing referenced env var or an unknown connector is reported on the
home menu (fail-fast) rather than at sync time. Choose **Sync data sources** in
the home menu to run a sync; per-connector cursors are persisted so each run only
pulls records changed since the last sync.

### Run

```bash
uv run productagents
```

Type an initiative (e.g. "Add enterprise SSO") and press Enter. Analyst panels update live and the strategist panel shows the final recommendation; each run appends a record to the organizational-memory DB.

**Evidence is pluggable.** A second input lets you point a run at a source: another bundled scenario name, or a path to a folder containing the evidence files (`customer_feedback.md` and `product_analytics.json` required; `market_intelligence.md`, `business_metrics.json`, `technical_context.md` optional). Each piece of evidence records its provenance, shown in the TUI and saved on the decision record. The default is the bundled `sample` scenario.

**Outcome learning.** After a decision, press `Ctrl+R` to open reflection mode, pick a past decision, and describe what happened. An Outcome Reflection Analyst compares predicted outcomes against reality and saves a prediction-accuracy score plus lessons to the DB (`DecisionStore`). Those reflections are automatically retrieved by hybrid (lexical + semantic) similarity and injected into the strategist's prompt on future decisions, closing the organizational-memory loop.

### Test

```bash
uv run pytest   # runs fully offline with a fake model — no API key required
```

---

## Why ProductAgents?

Because product management is not a prioritization framework — it is a decision-making system. Better decisions emerge when evidence, expertise, disagreement, governance, and learning work together. ProductAgents exists to make that process explicit, repeatable, and continuously improving.
</content>
