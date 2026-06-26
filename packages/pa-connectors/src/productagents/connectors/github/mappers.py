"""Pure GitHub-issue → canonical mapping. No I/O, no vendor terms in domain fields.

``core`` knows no GitHub exists; the vendor→canonical direction lives here, one
way. Vendor identity (issue number, url) is recorded on ``SourceRef`` only — the
agents reason over the domain fields (body/author/tags), never the lineage.
"""

from datetime import datetime

from productagents.core.models import CustomerFeedback
from productagents.core.models._base import fingerprint
from productagents.core.refs import SourceRef


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    # GitHub timestamps are ISO8601 with a trailing 'Z'; normalize to +00:00.
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def issue_to_feedback(issue: dict) -> CustomerFeedback:
    """Map one GitHub issue payload to a ``CustomerFeedback``."""
    title = issue.get("title") or ""
    body = issue.get("body") or ""
    user = issue.get("user") or {}
    return CustomerFeedback(
        body="\n\n".join(part for part in (title, body) if part),
        author=user.get("login"),
        submitted_at=_parse_dt(issue.get("created_at")),
        tags=[label["name"] for label in issue.get("labels", [])],
        source=SourceRef(
            connector="github",
            vendor_type="issue",
            vendor_id=str(issue["number"]),
            url=issue.get("html_url"),
        ),
        raw_fingerprint=fingerprint(issue),
    )
