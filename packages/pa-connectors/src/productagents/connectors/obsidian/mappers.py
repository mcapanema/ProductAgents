"""Pure Obsidian-note → canonical mapping. No I/O, no vendor terms in domain fields.

``core`` knows no Obsidian exists; the vendor→canonical direction lives here, one
way. Vendor identity (vault-relative path, file URI) is recorded on ``SourceRef``
only — the agents reason over the domain fields (body/tags), never the lineage.
"""

import re
from datetime import datetime
from pathlib import Path, PurePosixPath

from productagents.core.models import CustomerFeedback
from productagents.core.models._base import fingerprint
from productagents.core.refs import SourceRef

_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)
# ponytail: naive frontmatter parse — only a flat `tags: [a, b]` / `tags: a, b`
# line, no YAML lists. Swap in a real YAML parser only if pa-connectors ever
# gains one; the package contract is pa-core + httpx + stdlib.
_FM_TAGS = re.compile(r"^tags:\s*\[?([^\]\n]*)\]?\s*$", re.MULTILINE)
_INLINE_TAG = re.compile(r"(?:^|\s)#([\w/-]+)")


def split_note(text: str) -> tuple[str, str]:
    """Split a note into ``(frontmatter, body)``; frontmatter is '' when absent."""
    match = _FRONTMATTER.match(text)
    if not match:
        return "", text
    return match.group(1), text[match.end() :]


def extract_tags(frontmatter: str, body: str) -> list[str]:
    """Frontmatter ``tags:`` + inline ``#tags``, deduped, order-preserving."""
    tags: list[str] = []
    fm = _FM_TAGS.search(frontmatter)
    if fm:
        tags += [t.strip().strip("'\"") for t in fm.group(1).split(",") if t.strip()]
    tags += _INLINE_TAG.findall(body)
    return list(dict.fromkeys(tags))


def note_to_feedback(
    path: Path, vault: Path, text: str, mtime: datetime
) -> CustomerFeedback:
    """Map one vault note to a ``CustomerFeedback``."""
    frontmatter, body = split_note(text)
    relpath = str(PurePosixPath(path.relative_to(vault)))
    return CustomerFeedback(
        body="\n\n".join(part for part in (path.stem, body.strip()) if part),
        submitted_at=mtime,
        tags=extract_tags(frontmatter, body),
        source=SourceRef(
            connector="obsidian",
            vendor_type="note",
            vendor_id=relpath,
            url=path.as_uri(),
        ),
        raw_fingerprint=fingerprint({"path": relpath, "text": text}),
    )
