# ProductAgents

> ProductAgents is a multi-agent framework for product decision-making under uncertainty.

Inspired by organizational decision-making systems and multi-agent architectures, ProductAgents models how high-performing product organizations evaluate opportunities, challenge assumptions, manage risk, and make strategic decisions.

The framework is built around a simple idea:

> The goal is not to build a smarter AI.
>
> The goal is to build a smarter decision-making process.

Real organizations do not rely on a single person to decide what to build next. Product decisions emerge from the interaction of customer insights, business constraints, technical realities, market signals, strategic goals, and healthy disagreement between experts.

ProductAgents brings those dynamics into a transparent, traceable, and configurable multi-agent system.

---

## Vision

Product management is fundamentally a discipline of decision-making under uncertainty.

Teams must continuously answer questions such as:

- Should we build this feature?
- Is this problem worth solving?
- What should we prioritize next?
- Does this align with our strategy?
- Are we underestimating the risks?
- What are we choosing not to do?

Today, these decisions are often scattered across documents, meetings, dashboards, Slack threads, and intuition.

ProductAgents aims to provide a structured decision engine that transforms organizational knowledge into defensible product decisions.

Every recommendation is:

- Evidence-based
- Fully traceable
- Open to challenge
- Risk-assessed
- Governed through explicit approval
- Continuously improved through learning

---

## Core Principles

### Specialization

Different perspectives provide different signals.

Customer insights, business metrics, technical constraints, and market dynamics should not be collapsed into a single summary too early.

Disagreement is often more valuable than consensus.

### Structured Disagreement

Healthy product organizations challenge their own assumptions.

ProductAgents explicitly creates opposing viewpoints and debate loops before a decision is made.

### Transparency

Every decision should be explainable.

The framework preserves:

- Analyst reports
- Debate transcripts
- Risk assessments
- Approval decisions
- Outcome reviews

### Learning

Every decision creates data.

The system continuously reflects on previous recommendations and uses those learnings to improve future decisions.

---

## General Architecture

ProductAgents follows a seven-stage decision-making architecture — a stable
pipeline that turns raw evidence into governed, defensible product decisions and
learns from every outcome:

<p align="center">
  <img src="docs/images/general-architecture.png" alt="General Architecture — the seven-stage pipeline: Evidence Collection, Perspective Formation, Structured Disagreement, Decision Proposal, Risk Evaluation, Governance Approval, and Outcome Learning, wrapped by a continuous learning loop." width="900">
</p>

This architecture remains stable while agents, integrations, and organizational workflows can be customized for each company.

Given a proposed initiative, ProductAgents gathers evidence, debates the opportunity, evaluates risks, and produces a recommendation with supporting rationale.

---

## Agent Architecture

Specialised agents are organised into teams — gathering evidence, debating it,
proposing a call, stress-testing risk, and governing the final decision.

<p align="center">
  <img src="docs/images/agent-architecture.png" alt="Agent Architecture — five teams in sequence: the Analyst Team (five parallel analysts), the Research Team (Opportunity Advocate vs. Skeptic), the Product Strategist, the Risk Team (five reviewers), and the Portfolio Manager (Approve / Reject / Request analysis)." width="900">
</p>

### Analyst Team

The Analyst Team gathers evidence from multiple dimensions of the business.

These agents run in parallel.

#### Customer Research Analyst

Analyzes:

- Customer interviews
- Support tickets
- Feedback repositories
- NPS data

Produces:

- Customer pain points
- Demand signals
- Evidence summaries

#### Product Analytics Analyst

Analyzes:

- Product usage
- Funnels
- Retention
- Adoption metrics

Produces:

- Behavioral insights
- Impact estimations
- Opportunity sizing

#### Market Analyst

Analyzes:

- Competitors
- Industry trends
- Product launches
- Market shifts

Produces:

- Competitive intelligence
- Market opportunities
- Strategic context

#### Business Analyst

Analyzes:

- Revenue
- Costs
- Company goals
- Strategic initiatives

Produces:

- Business impact assessments
- Goal alignment evaluations
- ROI considerations

#### Technical Analyst

Analyzes:

- Architecture
- Technical debt
- Dependencies
- Delivery complexity

Produces:

- Feasibility assessments
- Technical risks
- Effort estimations

---

### Research Team

The Research Team transforms evidence into arguments.

#### Opportunity Advocate

Argues:

> We should build this initiative.

Focuses on:

- Customer value
- Business impact
- Strategic opportunity
- Competitive advantage

#### Opportunity Skeptic

Argues:

> We should not build this initiative.

Focuses on:

- Opportunity cost
- Risk
- Complexity
- Uncertainty

These agents participate in multiple rounds of structured debate.

The debate transcript becomes part of the decision record.

---

### Product Strategist

The Product Strategist consumes:

- Analyst reports
- Debate transcripts
- Organizational context

Produces:

- Recommendation
- Priority assessment
- Confidence score
- Expected outcomes
- Decision rationale

---

### Risk Team

Before approval, recommendations pass through specialized risk reviewers.

#### Delivery Risk Reviewer

Evaluates execution feasibility.

#### Adoption Risk Reviewer

Evaluates customer adoption risk.

#### Strategic Risk Reviewer

Evaluates alignment with organizational goals.

#### Financial Risk Reviewer

Evaluates economic viability and expected return.

#### Organizational Risk Reviewer

Evaluates capacity and operational constraints.

---

### Product Portfolio Manager

The Product Portfolio Manager acts as the final decision authority.

Responsibilities include:

- Reviewing recommendations
- Considering portfolio trade-offs
- Balancing competing priorities
- Approving or rejecting initiatives

The Portfolio Manager does not ask:

> Is this a good idea?

Instead, it asks:

> Is this the best use of our limited resources right now?

---

## The Six Layers

ProductAgents is organized into six configurable layers — wrapped by a memory
that learns whether each decision was right.

<p align="center">
  <img src="docs/images/six-layers.png" alt="The Six Layers — Evidence Collection, Perspective Formation, Structured Disagreement, Decision Proposal, Risk Evaluation, and Governance Approval, plus the Organizational Memory loop that records decisions, measures outcomes, and feeds lessons back." width="900">
</p>

### Layer 1 — Evidence Collection

Gather facts from internal and external systems.

Examples:

- Analytics
- CRM
- Customer feedback
- Support systems
- Market intelligence

### Layer 2 — Perspective Formation

Generate independent viewpoints based on the collected evidence.

Examples:

- Customer perspective
- Business perspective
- Technical perspective
- Strategic perspective

### Layer 3 — Structured Disagreement

Create productive conflict through debate.

Opposing agents challenge assumptions and defend positions.

### Layer 4 — Decision Proposal

Generate recommendations based on evidence and debate outcomes.

### Layer 5 — Risk Evaluation

Assess delivery, adoption, strategic, financial, and organizational risks.

### Layer 6 — Governance Approval

Approve, reject, or request additional analysis.

---

## The Secret Weapon: Organizational Memory

Every completed decision becomes part of the organization's collective learning system.

Decision records include:

```json
{
  "initiative": "...",
  "recommendation": "...",
  "confidence": 0.0,
  "reasoning": "...",
  "expected_outcomes": []
}
```

Later, the framework evaluates actual outcomes:

```json
{
  "actual_outcomes": [],
  "prediction_accuracy": 0.0,
  "lessons_learned": []
}
```

This creates a continuous feedback loop that helps the system improve over time.

The goal is not simply to remember decisions.

The goal is to remember whether those decisions were correct.

---

## Design Goals

- Framework-first architecture
- Organization-agnostic by default
- Configurable agent ecosystem
- Transparent reasoning
- Human-in-the-loop governance
- Durable decision history
- Production-ready orchestration
- Extensible integrations

---

## Technology Stack

### Runtime

- Python 3.14
- uv

### Orchestration

- LangGraph

### Models

Provider-agnostic architecture supporting:

- OpenAI
- Anthropic
- Google Gemini
- Local models

### Structured Outputs

ProductAgents uses strongly typed schemas for critical decisions to improve reliability and traceability.

### Persistence

- Checkpointed graph execution
- Decision logs
- Reflection history
- Organizational memory

---

## Future Roadmap

Potential future workflows include:

- Roadmap prioritization
- Opportunity assessment
- Product strategy reviews
- Quarterly planning
- Feature investment decisions
- Build vs Buy analysis
- Product portfolio management
- Go-to-market readiness reviews

---

## Why ProductAgents?

Because product management is not a prioritization framework.

It is a decision-making system.

And better decisions emerge when evidence, expertise, disagreement, governance, and learning work together.

ProductAgents exists to make that process explicit, repeatable, and continuously improving.

## Running the Slice (first milestone)

This repository currently implements an end-to-end slice: five analysts
(Customer Research, Product Analytics, Market, Business, Technical) evaluate
evidence in parallel, an Opportunity Advocate and an Opportunity Skeptic debate
the initiative over several rounds, a strategist produces a recommendation, an
LLM-as-Judge quality gate scores the recommendation for evidence grounding and
rationale coherence (looping back to the strategist for revision if it does not
pass), a Risk Team of five reviewers (Delivery, Adoption, Strategic, Financial,
Organizational) assesses the recommendation, and a Product Portfolio Manager
produces an advisory verdict — then a human makes the binding call to approve,
reject, or request further analysis (with an optional note) directly in the TUI.
All stages run live in the TUI and are saved (with the full debate transcript,
judge verdict, risk assessments, advisory governance verdict, and human decision)
to `decisions.jsonl`.

Evidence is pluggable. By default the bundled `sample` scenario is loaded, but
the TUI's second input lets you point a run at a different source before pressing
Enter: type another bundled scenario name, or a filesystem path to any folder
containing the evidence files. A folder is read as a `DirectorySource` and must
contain `customer_feedback.md` and `product_analytics.json` (required) and may
include `market_intelligence.md`, `business_metrics.json`, and
`technical_context.md` (optional). Each piece of evidence records its provenance
(which source and file it came from); the provenance is shown in the TUI's
"Evidence Sources" panel and saved on the decision record.

After a decision is made, you can record how it actually turned out: press
`Ctrl+R` to open reflection mode, pick a past decision, and describe what
happened. An Outcome Reflection Analyst compares the predicted expected outcomes
against reality and produces a prediction-accuracy score and lessons learned,
saved to an append-only `outcomes.jsonl`. Those reflections are now automatically
retrieved by lexical relevance and injected into the strategist's prompt on future
decisions, closing the organizational-memory loop — the system continuously learns
whether past decisions were correct and applies those lessons to new choices.

The number of debate rounds is configurable (each round is one advocate
argument followed by one skeptic rebuttal):

```bash
export PRODUCTAGENTS_DEBATE_ROUNDS=2  # default is 2
```

The quality judge threshold and maximum retries are also configurable:

```bash
export PRODUCTAGENTS_JUDGE_THRESHOLD=0.7  # minimum score (0-1) for evidence grounding and rationale coherence; default is 0.7
export PRODUCTAGENTS_JUDGE_MAX_RETRIES=1  # how many times the judge can loop back to the strategist; 0 = score-only (no retries); default is 1
```

### Setup

```bash
uv sync
```

### Configure a model

Model selection is provider-agnostic. Set the model via environment variables
(defaults to `anthropic:claude-sonnet-4-6`).

The easiest way is to copy the template and edit it — `.env` is loaded
automatically on startup and is git-ignored:

```bash
cp .env.example .env
# then edit .env and set your provider API key
```

Any variable already exported in your shell takes precedence over `.env`.
You can still configure everything with plain `export`s instead:

```bash
export PRODUCTAGENTS_MODEL="anthropic:claude-sonnet-4-6"
# Provide the matching provider API key, e.g.:
export ANTHROPIC_API_KEY="sk-..."
```

To use another provider, set both variables, e.g.:

```bash
export PRODUCTAGENTS_MODEL="gpt-5.5"
export PRODUCTAGENTS_MODEL_PROVIDER="openai"
export OPENAI_API_KEY="sk-..."
```

#### OpenRouter free models

[OpenRouter](https://openrouter.ai) exposes many models — including a free
tier — behind one API key. Set an `openrouter:`-prefixed model id and your
OpenRouter key:

```bash
export PRODUCTAGENTS_MODEL="openrouter:deepseek/deepseek-chat-v3-0324:free"
export OPENROUTER_API_KEY="sk-or-..."
```

Leave `PRODUCTAGENTS_MODEL_PROVIDER` unset — the `openrouter:` prefix selects
the provider, and the `:free` suffix is preserved as part of the model id.

**Pick a model that supports tool/function calling.** Every stage in the
pipeline uses structured output (`with_structured_output`, which defaults to
function calling), so a free model without tool support will make each node
fall back to a placeholder result rather than fail loudly. Known-good free
options include `deepseek/deepseek-chat-v3-0324:free`,
`meta-llama/llama-3.3-70b-instruct:free`, and
`google/gemini-2.0-flash-exp:free`. Expect free-tier rate limits — runs may be
slower or occasionally throttled.

### Run

```bash
uv run productagents
```

Type an initiative (e.g. "Add enterprise SSO") and press Enter. The analyst
panels update live and the strategist panel shows the final recommendation.
Each run appends a record to `decisions.jsonl`.

### Test

```bash
uv run pytest
```

All tests run offline with a fake model — no API key required.
