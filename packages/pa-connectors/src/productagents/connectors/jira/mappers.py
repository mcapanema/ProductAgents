"""Pure Jira-issue → canonical mapping. No I/O, no vendor terms in domain fields.

``core`` knows no Jira exists; the vendor→canonical direction lives here, one
way. Vendor identity (issue key, browse url) is recorded on ``SourceRef`` only —
the agents reason over the domain fields (body/author/tags), never the lineage.

Jira Cloud's ``description`` is Atlassian Document Format (ADF) — a nested JSON
doc, not plain text. ``adf_to_text`` flattens its ``text`` leaves best-effort;
the ``summary`` is the primary body. ponytail: best-effort flatten, not a full
ADF renderer — upgrade to a real ADF parser only if rich structure must survive.
"""

from datetime import datetime

from productagents.core.models import CustomerFeedback
from productagents.core.models._base import fingerprint
from productagents.core.refs import SourceRef


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    # Jira timestamps are ISO8601 with a ``+0000``-style offset; fromisoformat
    # (3.11+) accepts both ``+HHMM`` and fractional seconds directly.
    return datetime.fromisoformat(value)


def adf_to_text(node: dict | None) -> str:
    """Concatenate every ``text`` leaf in an ADF document, depth-first."""
    if not node:
        return ""
    parts: list[str] = []

    def walk(n: dict) -> None:
        if isinstance(n.get("text"), str):
            parts.append(n["text"])
        for child in n.get("content") or ():
            walk(child)

    walk(node)
    return "".join(parts)


def issue_to_feedback(issue: dict, *, base_url: str) -> CustomerFeedback:
    """Map one Jira issue payload to a ``CustomerFeedback``."""
    fields = issue.get("fields") or {}
    summary = fields.get("summary") or ""
    description = adf_to_text(fields.get("description"))
    reporter = fields.get("reporter") or {}
    key = issue["key"]
    return CustomerFeedback(
        body="\n\n".join(part for part in (summary, description) if part),
        author=reporter.get("displayName"),
        submitted_at=_parse_dt(fields.get("created")),
        tags=list(fields.get("labels") or []),
        source=SourceRef(
            connector="jira",
            vendor_type="issue",
            vendor_id=key,
            url=f"{base_url.rstrip('/')}/browse/{key}",
        ),
        raw_fingerprint=fingerprint(issue),
    )
