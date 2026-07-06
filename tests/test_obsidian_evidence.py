"""The Obsidian evidence source: tag-routed vault notes → the five Evidence fields."""

from pathlib import Path

from productagents.agents.evidence import collect_evidence
from productagents.connectors.obsidian.evidence import resolve_vault


def _write(vault: Path, relpath: str, text: str) -> Path:
    path = vault / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_resolver_declines_unprefixed_specs(tmp_path):
    assert resolve_vault("sample", None) is None
    assert resolve_vault(str(tmp_path), None) is None  # plain dir stays DirectorySource


def test_resolver_declines_missing_vault(tmp_path):
    assert resolve_vault(f"obsidian:{tmp_path / 'nope'}", None) is None


def test_collect_routes_tagged_notes_to_fields(tmp_path):
    _write(
        tmp_path,
        "interviews/Churn interview.md",
        "---\ntags: [customer-feedback]\n---\nExport is slow.",
    )
    _write(tmp_path, "Competitors.md", "Rival shipped export. #market")
    _write(tmp_path, "Funnel.md", "Drop-off at step 3. #product-analytics")
    _write(tmp_path, "Runway.md", "Burn is fine. #business")
    _write(tmp_path, "Arch.md", "Export is single-threaded. #technical")
    _write(tmp_path, "Journal.md", "no tag, never evidence")

    source = resolve_vault(f"obsidian:{tmp_path}", None)
    assert source is not None
    evidence = source.collect()

    assert "Export is slow." in evidence.customer_feedback
    assert "Rival shipped export." in evidence.market_intelligence
    assert "Drop-off at step 3." in evidence.product_analytics["notes"]
    assert "Burn is fine." in evidence.business_metrics["notes"]
    assert "single-threaded" in evidence.technical_context
    assert "no tag" not in evidence.customer_feedback
    assert {ref.field for ref in evidence.sources} == {
        "customer_feedback",
        "product_analytics",
        "market_intelligence",
        "business_metrics",
        "technical_context",
    }


def test_collect_handles_sparse_vault(tmp_path):
    _write(tmp_path, "note.md", "Users want dark mode. #customer-feedback")

    source = resolve_vault(f"obsidian:{tmp_path}", None)
    assert source is not None
    evidence = source.collect()

    assert "dark mode" in evidence.customer_feedback
    assert evidence.product_analytics == {}
    assert evidence.business_metrics == {}
    assert evidence.market_intelligence == ""


def test_collect_evidence_resolves_obsidian_prefix_end_to_end(tmp_path):
    _write(tmp_path, "note.md", "Users want dark mode. #customer-feedback")

    evidence = collect_evidence(f"obsidian:{tmp_path}")

    assert evidence.scenario == f"obsidian:{tmp_path.name}"
    assert "dark mode" in evidence.customer_feedback
