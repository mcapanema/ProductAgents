# ProductAgents V3 — Local Platform Architecture

You are helping me design and implement the next major version of ProductAgents.

Do not treat this as a UI redesign.

Do not treat this as a refactor.

Treat this as an architectural evolution of the entire platform.

Your job is to think like a Principal Software Architect responsible for building a platform that should still feel well designed five years from now.

Your priorities should always be:

1. Simplicity
2. Separation of concerns
3. Extensibility
4. Long-term maintainability
5. Excellent developer experience

Before writing code, fully understand the concepts below.

Do not immediately start implementing.

First review the architecture, challenge weak decisions, identify risks, suggest improvements, and then produce an implementation roadmap.

Only after the architecture is sound should implementation begin.

---

# Project Vision

ProductAgents is no longer just a multi-agent framework.

It is becoming a local operating environment for product decision-making.

The project is inspired by TradingAgents, but its purpose is much broader.

TradingAgents models how investment firms make decisions.

ProductAgents models how modern product organizations make decisions.

The long-term goal is to create an operating system for product decision-making.

Agents are only one component of that system.

The platform should eventually support:

- Initiative evaluation
- Product strategy
- Roadmap planning
- Portfolio management
- Opportunity assessment
- Quarterly planning
- Build vs Buy analysis
- Risk analysis
- Future workflows not yet imagined

The architecture should optimize for those future workflows without overengineering today's implementation.

---

# Local-First Philosophy

This version should intentionally remain local-first.

Do not introduce a distributed client/server architecture.

Do not introduce authentication.

Do not introduce remote APIs.

Do not optimize for cloud deployment.

Everything should execute locally.

The GUI, CLI, runtime, persistence, connectors, knowledge layer, and workflow engine all run on the same machine.

However...

The architecture should naturally evolve into a client/server model later without requiring major rewrites.

Future evolution should be additive.

Not disruptive.

---

# Core Philosophy

ProductAgents is not an AI application.

It is an operating environment for product decision-making.

Agents are consumers of the platform.

Not the platform itself.

The architecture should reflect this.

---

# Presentation Must Be Independent

Separate Presentation from Execution completely.

Presentation should never know how workflows execute.

Presentation should never know LangGraph.

Presentation should never know connectors.

Presentation should never know persistence.

Presentation communicates exclusively with the Application Layer.

Never bypass that boundary.

---

# Architectural Layers

The architecture should evolve into:

Presentation

↓

Application Services

↓

Runtime

↓

Core Engine

↓

Knowledge Layer

↓

Persistence

↓

Connector Layer

↓

External Systems

Each layer has one responsibility.

Dependencies should only point downward.

---

# Presentation Layer

The Presentation Layer is simply an adapter.

Current adapters:

- Desktop GUI
- CLI

Future adapters:

- REST API
- MCP Server
- IDE Extension
- VS Code Extension
- Claude Code
- CI/CD integrations

Presentation should never own business logic.

Presentation should only invoke Application Services.

---

# Application Services

Introduce a new Application Layer.

This becomes the stable API of the platform.

Everything should go through Application Services.

Examples:

EvaluationService

WorkflowService

DecisionService

ConnectorService

MemoryService

ConfigurationService

PromptService

PluginService

SessionService

WorkspaceService

The GUI should never call LangGraph.

The CLI should never call LangGraph.

Future REST APIs should never call LangGraph.

Everything goes through Application Services.

---

# Runtime

Introduce a Runtime.

This layer does not contain product logic.

Instead it manages execution.

Responsibilities:

- Workflow execution
- Session lifecycle
- Event publication
- Plugin loading
- Resource lifecycle
- Cancellation
- Progress tracking
- Scheduling
- Streaming
- Execution state

Think of this as the operating system of ProductAgents.

---

# Core Engine

The Core Engine contains:

- Agents
- LangGraph
- Knowledge Services
- Decision logic
- Debate logic
- Risk evaluation

The Engine should know nothing about the GUI.

The Engine should know nothing about the CLI.

---

# Workspaces

Introduce Workspaces.

Everything belongs to a Workspace.

A Workspace represents a product organization.

It owns:

- Connector configuration
- Prompt registry
- Organizational memory
- Knowledge base
- Plugins
- Sessions
- Decisions
- Settings
- Secrets
- Model providers

Think similarly to:

VS Code Workspaces

GitHub Organizations

Linear Teams

---

# Sessions

Introduce Sessions.

A Session represents one execution of ProductAgents.

It owns:

- Workflow
- Events
- Logs
- Decisions
- Evidence
- Debate transcripts
- Outputs
- Runtime state

Sessions should feel similar to running a GitHub Actions workflow.

---

# Workflows

Workflows become first-class citizens.

The application is no longer "running LangGraph."

The application is executing a Workflow.

Examples:

Evaluate Initiative

Roadmap Prioritization

Quarterly Planning

Product Strategy Review

Future workflows should require zero UI changes.

Only registration.

---

# Artifacts

Everything should become a persistent artifact.

Examples:

Decision

Evidence Report

Debate Transcript

Risk Assessment

Reflection

Prompt

Workflow Definition

Knowledge Snapshot

Configuration

Artifacts should be:

Versioned

Exportable

Diffable

Traceable

---

# Organizational Memory

Organizational Memory becomes one of the core systems.

Every workflow contributes.

Store:

Evidence

Agent reports

Debates

Recommendations

Approvals

Predictions

Actual outcomes

Lessons learned

The purpose is not merely recording history.

The purpose is improving future decision quality.

---

# Event Bus

Introduce an Event Bus.

Everything publishes events.

Examples:

AgentStarted

AgentProgress

AgentFinished

WorkflowStarted

WorkflowFinished

ConnectorStarted

ConnectorFinished

ToolCalled

DebateStarted

DebateFinished

DecisionCreated

RiskRejected

WorkflowCancelled

The Event Bus should be the primary communication mechanism inside the runtime.

---

# Event Store

Persist runtime events.

Allow:

Replay

Timeline visualization

Debugging

Execution history

Future analytics

The Event Store complements Organizational Memory.

Organizational Memory stores decisions.

The Event Store stores execution.

---

# Plugin Architecture

Everything should be pluggable.

Not only connectors.

Examples:

Connector plugins

Agent plugins

Workflow plugins

Knowledge Service plugins

Prompt Packs

Tool plugins

Output formatters

Risk evaluators

Evidence collectors

The core should discover plugins dynamically.

---

# GUI Philosophy

Do not build another chat application.

Avoid copying ChatGPT.

Instead take inspiration from:

VS Code

Linear

LangSmith

GitHub Actions

Datadog

The interface should visualize reasoning.

Not conversations.

The application should feel like an IDE for decision-making.

---

# UI Information Architecture

Think in terms of explorers instead of conversations.

Example:

Workspace

├── Sessions

├── Workflows

├── Decisions

├── Organizational Memory

├── Connectors

├── Knowledge

├── Prompts

├── Plugins

├── Models

└── Settings

The main panel displays the selected resource.

---

# Decision Explorer

Create a Decision Explorer.

Users should browse historical decisions similarly to browsing Git history.

Each decision contains:

Evidence

Debate

Risk analysis

Recommendation

Approval

Outcome

Reflection

This will eventually become one of the most valuable parts of ProductAgents.

---

# Connector Management

Expose connectors as first-class platform components.

Users should see:

Connection status

Synchronization status

Last sync

Health

Statistics

Configuration

Connector management should reinforce that connectors are platform infrastructure.

---

# Prompt Registry

Prompts become versioned assets.

Users should:

Browse prompts

Compare versions

Rollback

Edit

Inspect history

Prompts become part of organizational knowledge.

---

# Streaming UI

The interface should feel alive.

Execution should stream.

Not poll.

Examples:

Customer Analyst starts.

Progress updates.

Tool execution.

Evidence discovered.

Debate begins.

Decision created.

Risk review completed.

Workflow finished.

Everything updates incrementally.

---

# CLI Philosophy

Treat the CLI as a first-class client.

The CLI should never implement business logic.

It should simply invoke Application Services.

The GUI and CLI should behave identically.

Future adapters should reuse the same Application Layer.

---

# Packaging

The first implementation should be a self-contained local application.

Build:

- Desktop GUI
- Companion CLI

Both should use the same Application Layer.

Use:

Tauri + React

for the desktop application.

Continue using Python for the core platform.

Bundle the application as a single installable desktop application while preserving the existing Python architecture.

The packaging mechanism should not influence the platform architecture.

Keep the architecture independent from packaging.

---

# Technology

Current stack:

Python

uv

LangGraph

Pydantic

Strong typing

Async-first

Do not replace these technologies unless there is a compelling architectural reason.

---

# Deliverables

Before implementing anything:

Review this architecture critically.

Challenge assumptions.

Suggest improvements.

Identify weaknesses.

Recommend refinements.

Then produce:

1. Overall implementation strategy

2. Migration strategy from V2

3. Proposed package structure

4. Runtime architecture

5. Application Services architecture

6. Workspace model

7. Session model

8. Workflow architecture

9. Event Bus architecture

10. Event Store architecture

11. Plugin architecture

12. GUI architecture

13. CLI architecture

14. Tauri integration strategy

15. Packaging strategy

16. Development roadmap

17. Risks and tradeoffs

Only after completing the architecture review should implementation begin.

The resulting ProductAgents V3 should feel less like an AI framework and more like a modern local operating environment for product decision-making.
