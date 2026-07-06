"""Obsidian vault → per-run Evidence: tagged notes feed all five analysts.

The synced canonical store only reaches the Customer Research analyst
(``AgentContext.feedback``), so this second surface routes vault notes into the
``Evidence`` fields every analyst consumes. Registered as a resolver under the
``productagents.evidence_sources`` entry-point group; claimed by spec prefix:

    --evidence obsidian:<vault-path>

Tag → field routing (a note may carry several; untagged notes are ignored —
a vault holds everything, only tagged notes are evidence):

    #customer-feedback → customer_feedback   #business  → business_metrics
    #product-analytics → product_analytics   #technical → technical_context
    #market            → market_intelligence

This satisfies pa-agents' ``EvidenceSource`` Protocol structurally —
pa-connectors never imports pa-agents (layer rule).
"""

from pathlib import Path

from productagents.connectors.obsidian.connector import iter_notes
from productagents.connectors.obsidian.mappers import extract_tags, split_note
from productagents.core.models import Evidence, EvidenceSourceRef

_PREFIX = "obsidian:"
_TAG_FIELDS = {
    "customer-feedback": "customer_feedback",
    "product-analytics": "product_analytics",
    "market": "market_intelligence",
    "business": "business_metrics",
    "technical": "technical_context",
}


class ObsidianVaultSource:
    """Collects tagged vault notes into the five ``Evidence`` fields."""

    def __init__(self, vault: Path) -> None:
        self._vault = vault

    def collect(self) -> Evidence:
        texts: dict[str, list[str]] = {field: [] for field in _TAG_FIELDS.values()}
        refs: list[EvidenceSourceRef] = []
        origin = f"obsidian:{self._vault}"
        for path in iter_notes(self._vault):
            frontmatter, body = split_note(path.read_text(encoding="utf-8"))
            tags = set(extract_tags(frontmatter, body))
            for tag, field in _TAG_FIELDS.items():
                if tag not in tags:
                    continue
                texts[field].append(f"# {path.stem}\n\n{body.strip()}")
                refs.append(
                    EvidenceSourceRef(field=field, source=origin, location=str(path))
                )

        def joined(field: str) -> str:
            return "\n\n---\n\n".join(texts[field])

        def as_dict(field: str) -> dict:
            # ponytail: markdown wrapped as {"notes": …} — these two Evidence
            # fields are dicts; real metric extraction belongs to a future
            # metrics connector, not an evidence source.
            return {"notes": joined(field)} if texts[field] else {}

        return Evidence(
            scenario=f"obsidian:{self._vault.name}",
            customer_feedback=joined("customer_feedback"),
            product_analytics=as_dict("product_analytics"),
            market_intelligence=joined("market_intelligence"),
            business_metrics=as_dict("business_metrics"),
            technical_context=joined("technical_context"),
            sources=refs,
        )


def resolve_vault(spec: str, base_dir: Path | None) -> ObsidianVaultSource | None:
    """Claim ``obsidian:<path>`` specs; ``None`` lets the next resolver try.

    A missing vault also returns ``None`` so ``collect_evidence`` raises its own
    friendly ``EvidenceError`` — pa-connectors must not import pa-agents' error
    type (layer rule).
    """
    if not spec.startswith(_PREFIX):
        return None
    vault = Path(spec[len(_PREFIX) :]).expanduser().resolve()
    return ObsidianVaultSource(vault) if vault.is_dir() else None
