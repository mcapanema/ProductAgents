# productagents.core — the canonical vocabulary

`pa-core` is the dependency sink: it imports **only** stdlib + `pydantic` +
`python-dotenv`. No `httpx`, `langchain`, `langgraph`, `sqlalchemy`, `textual`
(enforced by import-linter). Everything else in the workspace depends on this.

## Layout

- `enums.py` — shared `Literal` vocabularies (`Verdict`, `RiskLevel`, `Priority`,
  `Sentiment`, statuses, …). Kept as `Literal` aliases, not `enum.Enum`.
- `ids.py` — `new_id()` + branded `NewType` identifiers (`InitiativeId`, …).
  Branding is static-only; at runtime these are `str`.
- `refs.py` — `SourceRef` (connector + vendor entity + vendor id lineage) and
  `ExternalRef`. `SourceRef.manual()` is the provenance for user/platform-created
  records.
- `models/` — canonical models split by **bounded context**:
  - `_base.py` — `CanonicalModel` (id, source, timestamps, `raw_fingerprint`,
    `extensions`) + `fingerprint()`.
  - `discovery.py` · `planning.py` · `strategy.py` · `measurement.py` — synced
    entities (subclass `CanonicalModel`).
  - `decision.py` — the decision-run records and LLM-output schemas migrated from
    v1 `schemas.py`. These are platform-*produced*, so plain `BaseModel`, **not**
    `CanonicalModel`.
  - `__init__.py` — the public re-export surface. **Import from
    `productagents.core.models`, never from the submodules.**

## Rules that matter

- **Synced models subclass `CanonicalModel`; decision/LLM-output models don't.**
  Provenance belongs to things connectors ingest, not to things agents emit.
- **Agents reason over domain fields only** — never `source`, `extensions`, or the
  sync metadata. Mappers (Phase 4) must keep vendor terms out of domain fields;
  `tests/canonical_harness.py` enforces this.
- **All `CanonicalModel` fields are defaulted**, so `Initiative(title=...,
  description=...)` works for manual creation and gets `SourceRef.manual()`.
- **`core` knows no vendor exists.** No `from_jira()` constructors; mapping is
  vendor → canonical inside a connector, one-way.
