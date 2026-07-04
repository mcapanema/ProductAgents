"""Validate a WorkflowDefinition against the always-runnable guarantee.

The key check is rank-based state-availability: LangGraph runs nodes in parallel
super-steps, so a node may read a key produced by ANOTHER branch as long as that
producer runs in an earlier super-step. Rank = longest path from START over the
graph's edges; a read is satisfied iff some strictly-earlier-rank node writes it
(or START provides it). This is why the default validates despite there being no
explicit ``recall -> strategist`` edge (recall ranks 1, strategist ranks 3).
"""

from __future__ import annotations

from collections import deque

from productagents.agents.node_kinds import KIND_REGISTRY
from productagents.core.models import END_ID, START_ID, WorkflowDefinition

_START_KEYS = frozenset({"initiative", "evidence"})


def _ranks(defn: WorkflowDefinition, node_ids: set[str]) -> dict[str, int] | None:
    """Longest-path rank from START_ID over defn.edges; None if a cycle exists.

    ponytail: uses every edge, not just non-conditional ones. WorkflowEdgeDef's
    `conditional` flag is documented as display-only (routing is intrinsic to
    the NodeKind's router/router_targets, e.g. strategist->judge, judge->risk
    in the default workflow are both conditional=True yet purely forward) —
    there is currently
    no way for a real back-edge to land in defn.edges, so filtering by
    `conditional` only drops structurally necessary edges and produces false
    cycles/false-missing-rank for nodes like judge/risk. If the GUI ever starts
    persisting a genuine back-edge for retry-loop display, this will need a
    real forward/back distinction (e.g. by rank once known) instead of the
    `conditional` flag.
    """
    succ: dict[str, list[str]] = {n: [] for n in (*node_ids, START_ID)}
    indeg: dict[str, int] = dict.fromkeys(node_ids, 0)
    for e in defn.edges:
        if e.target not in node_ids:
            continue  # END_ID, or an unknown endpoint already reported
        if e.source != START_ID and e.source not in node_ids:
            continue  # unknown endpoint already reported
        succ[e.source].append(e.target)
        if e.source != START_ID:
            indeg[e.target] += 1

    rank = dict.fromkeys(node_ids, 0)
    for t in succ[START_ID]:
        rank[t] = max(rank[t], 1)

    queue = deque(n for n in node_ids if indeg[n] == 0)
    seen = 0
    while queue:
        n = queue.popleft()
        seen += 1
        for m in succ[n]:
            rank[m] = max(rank[m], rank[n] + 1)
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
    if seen != len(node_ids):
        return None  # cycle
    return rank


def validate_definition(defn: WorkflowDefinition) -> list[str]:
    """Return validation errors; an empty list means the definition is runnable."""
    errors: list[str] = []
    node_ids = [n.id for n in defn.nodes]

    if not defn.nodes:
        errors.append("workflow has no nodes")
    if len(set(node_ids)) != len(node_ids):
        errors.append("duplicate node ids")

    id_set = set(node_ids)
    seen_singletons: set[str] = set()
    for n in defn.nodes:
        kind = KIND_REGISTRY.get(n.kind)
        if kind is None:
            errors.append(f"node {n.id!r} has unknown kind {n.kind!r}")
            continue
        if kind.singleton:
            if n.id != n.kind:
                errors.append(f"singleton node {n.id!r} must use id == kind {n.kind!r}")
            if n.kind in seen_singletons:
                errors.append(f"singleton kind {n.kind!r} appears more than once")
            seen_singletons.add(n.kind)

    for e in defn.edges:
        for endpoint in (e.source, e.target):
            if endpoint not in id_set and endpoint not in (START_ID, END_ID):
                errors.append(f"edge references unknown node {endpoint!r}")

    if errors:
        return errors  # structural errors first — availability needs a clean graph

    ranks = _ranks(defn, id_set)
    if ranks is None:
        errors.append("graph has a cycle in its forward edges")
        return errors

    reachable = {START_ID}
    queue = deque([START_ID])
    while queue:
        cur = queue.popleft()
        for e in defn.edges:
            if e.source == cur and e.target in id_set and e.target not in reachable:
                reachable.add(e.target)
                queue.append(e.target)
    for n in defn.nodes:
        if n.id not in reachable:
            errors.append(f"node {n.id!r} is unreachable from start")
    if errors:
        return errors

    for n in defn.nodes:
        kind = KIND_REGISTRY[n.kind]
        available = set(_START_KEYS)
        for other in defn.nodes:
            if ranks[other.id] < ranks[n.id]:
                available |= KIND_REGISTRY[other.kind].writes
        missing = kind.reads - available
        if missing:
            errors.append(
                f"node {n.id!r} needs {sorted(missing)} but no earlier node produces it"
            )

    if not any(e.target == END_ID for e in defn.edges):
        errors.append("no node reaches the end")

    return errors
