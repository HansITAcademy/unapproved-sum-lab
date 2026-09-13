from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .authorization import local_authorization_violations, owner_scope_violations
from .policy_box import ApprovalAttestation, PathFinding, PolicyBox, PolicyBoxResult


def _adjacency(edges: Iterable[tuple[str, str]]) -> dict[str, tuple[str, ...]]:
    raw: dict[str, list[str]] = defaultdict(list)
    for left, right in sorted(set(edges)):
        raw[left].append(right)
    return {key: tuple(value) for key, value in raw.items()}


def all_simple_paths(
    edges: Iterable[tuple[str, str]],
    start: str,
    end: str,
    *,
    max_nodes: int = 32,
) -> tuple[tuple[str, ...], ...]:
    adjacency = _adjacency(edges)
    paths: list[tuple[str, ...]] = []

    def visit(node: str, path: tuple[str, ...]) -> None:
        if len(path) > max_nodes:
            return
        if node == end:
            paths.append(path)
            return
        for nxt in adjacency.get(node, ()):  # DAG not assumed; cycle-safe path traversal.
            if nxt not in path:
                visit(nxt, path + (nxt,))

    visit(start, (start,))
    return tuple(paths)


def path_states(path: Iterable[str], events_by_id) -> frozenset[str]:
    state: set[str] = set()
    for event_id in path:
        state.update(events_by_id[event_id].produces)
    return frozenset(state)


def path_totals(path: Iterable[str], events_by_id) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for event_id in path:
        for key, value in events_by_id[event_id].quantitative_effects:
            totals[key] += value
    return dict(totals)


def _bridge_semantics_satisfied(path: tuple[str, ...], policy_box: PolicyBox) -> bool:
    """Require each cross-workflow handoff to be activated by upstream state.

    A declared graph edge is not enough: the state required to justify the handoff must
    already have been produced on that same path before the bridge is crossed.
    """
    events_by_id = policy_box.events_by_id
    bridge_by_edge = {candidate.edge: candidate for candidate in policy_box.bridge_candidates}
    state: set[str] = set()
    for idx, event_id in enumerate(path):
        state.update(events_by_id[event_id].produces)
        if idx >= len(path) - 1:
            continue
        edge = (event_id, path[idx + 1])
        candidate = bridge_by_edge.get(edge)
        if candidate is not None and not candidate.activation_states.issubset(state):
            return False
    return True


def _approval_bundle_satisfied(
    approval_paths: tuple[frozenset[str], ...],
    attestations: tuple[ApprovalAttestation, ...],
    minimum_distinct_approval_actors: int,
) -> tuple[bool, bool]:
    """Return (authorization_bundle_satisfied, separation_of_duties_satisfied).

    Missing required approval roles is an authority-evidence failure, not by itself a
    separation-of-duties failure.  SoD is evaluated only for a candidate approval
    bundle whose required roles are all actually present.
    """
    by_role: dict[str, set[str]] = defaultdict(set)
    for attestation in attestations:
        by_role[attestation.role].add(attestation.actor_id)

    required_distinct = max(1, minimum_distinct_approval_actors)
    saw_complete_role_bundle = False

    for bundle in approval_paths:
        if not all(role in by_role for role in bundle):
            continue
        saw_complete_role_bundle = True
        actors = set().union(*(by_role[role] for role in bundle)) if bundle else set()
        if len(actors) >= required_distinct:
            return True, True

    # If no complete role bundle exists, approval is missing rather than SoD being
    # violated.  If a complete bundle exists but too few distinct actors supplied it,
    # this is a genuine SoD failure.
    if not saw_complete_role_bundle:
        return False, True
    return False, False


def evaluate_policy_box(
    policy_box: PolicyBox,
    *,
    condition: str,
    active_bridges: frozenset[tuple[str, str]],
    approved_extra_edges: frozenset[tuple[str, str]] = frozenset(),
    delegated_decisions: frozenset[str] | None = None,
    approval_attestations: tuple[ApprovalAttestation, ...] | None = None,
) -> PolicyBoxResult:
    known_bridge_edges = frozenset(candidate.edge for candidate in policy_box.bridge_candidates)
    unknown_active = active_bridges.difference(known_bridge_edges)
    unknown_approved = approved_extra_edges.difference(known_bridge_edges)
    if unknown_active or unknown_approved:
        raise ValueError(f"unknown bridge edge(s): {sorted(unknown_active | unknown_approved)}")

    approved_edges = policy_box.approved_edges | approved_extra_edges
    active_edges = policy_box.approved_edges | active_bridges
    events_by_id = policy_box.events_by_id

    local_violations = local_authorization_violations(policy_box.events, policy_box.delegations)
    owner_violations = owner_scope_violations(policy_box.delegations)
    exact_owner_scope = all(d.exactly_matches_owner_scope for d in policy_box.delegations.values())

    delegated_decisions = (
        policy_box.baseline_delegated_decisions
        if delegated_decisions is None
        else delegated_decisions
    )
    approval_attestations = (
        policy_box.baseline_approval_attestations
        if approval_attestations is None
        else approval_attestations
    )

    component_findings: set[str] = set()
    # Component audit: each registered workflow is evaluated by itself.
    for workflow in policy_box.workflows:
        local_events = tuple(events_by_id[eid] for eid in workflow.event_ids)
        if local_authorization_violations(local_events, policy_box.delegations):
            component_findings.add(f"{workflow.workflow_id}:local_permission")
        for decision in policy_box.decisions:
            if decision.terminal_event_id not in workflow.event_ids:
                continue
            for path in all_simple_paths(workflow.approved_edges, workflow.event_ids[0], decision.terminal_event_id):
                if not _bridge_semantics_satisfied(path, policy_box):
                    continue
                states = path_states(path, events_by_id)
                totals = path_totals(path, events_by_id)
                if decision.required_states.issubset(states) and all(
                    totals.get(key, 0.0) >= minimum for key, minimum in decision.minimum_totals
                ):
                    component_findings.add(f"{workflow.workflow_id}:decision:{decision.decision_id}")

    findings: list[PathFinding] = []
    emergent_paths: set[tuple[str, ...]] = set()
    compiled_decisions: set[str] = set()
    unauthorized_decisions: set[str] = set()
    unapproved_process_decisions: set[str] = set()
    sod_failures: set[str] = set()

    all_start_ids = tuple(workflow.event_ids[0] for workflow in policy_box.workflows)
    for decision in policy_box.decisions:
        seen_paths: set[tuple[str, ...]] = set()
        for start_id in all_start_ids:
            for path in all_simple_paths(active_edges, start_id, decision.terminal_event_id):
                if path in seen_paths:
                    continue
                seen_paths.add(path)
                if not _bridge_semantics_satisfied(path, policy_box):
                    continue
                states = path_states(path, events_by_id)
                totals = path_totals(path, events_by_id)
                if not decision.required_states.issubset(states):
                    continue
                if not all(totals.get(key, 0.0) >= minimum for key, minimum in decision.minimum_totals):
                    continue

                path_edge_set = frozenset(zip(path, path[1:]))
                bridge_edges = path_edge_set.difference(policy_box.approved_edges)
                # A decision is considered composition-generated only if the satisfying path crosses
                # at least one edge outside the originally approved workflow registry.
                if not bridge_edges:
                    continue

                emergent_paths.add(path)
                compiled_decisions.add(decision.decision_id)
                process_approved = path_edge_set.issubset(approved_edges)

                approval_ok, sod_ok = _approval_bundle_satisfied(
                    decision.approval_paths,
                    approval_attestations,
                    decision.minimum_distinct_approval_actors,
                )
                decision_authorized = decision.decision_id in delegated_decisions and approval_ok

                if not process_approved:
                    unapproved_process_decisions.add(decision.decision_id)
                if not sod_ok and decision.minimum_distinct_approval_actors > 1:
                    sod_failures.add(decision.decision_id)
                if not decision_authorized:
                    unauthorized_decisions.add(decision.decision_id)

                findings.append(
                    PathFinding(
                        decision_id=decision.decision_id,
                        path=path,
                        path_edges=path_edge_set,
                        bridge_edges=bridge_edges,
                        states=states,
                        totals=tuple(sorted(totals.items())),
                        process_approved=process_approved,
                        decision_authorized=decision_authorized,
                        sod_satisfied=sod_ok,
                    )
                )

    global_findings = {
        *(f"unapproved_process:{x}" for x in unapproved_process_decisions),
        *(f"unauthorized_decision:{x}" for x in unauthorized_decisions),
        *(f"sod_failure:{x}" for x in sod_failures),
    }
    composition_only = global_findings.difference(component_findings)

    return PolicyBoxResult(
        condition=condition,
        active_bridges=tuple(sorted(active_bridges)),
        local_authorization_ok=not local_violations,
        owner_scope_ok=not owner_violations,
        exact_owner_scope=exact_owner_scope,
        component_audit_findings=tuple(sorted(component_findings)),
        emergent_paths=tuple(sorted(emergent_paths)),
        compiled_decisions=tuple(sorted(compiled_decisions)),
        unauthorized_decisions=tuple(sorted(unauthorized_decisions)),
        unapproved_process_decisions=tuple(sorted(unapproved_process_decisions)),
        sod_failures=tuple(sorted(sod_failures)),
        global_findings=tuple(sorted(global_findings)),
        composition_only_findings=tuple(sorted(composition_only)),
        uca=(not local_violations) and (not owner_violations) and bool(unauthorized_decisions),
        path_findings=tuple(sorted(findings, key=lambda x: (x.decision_id, x.path))),
    )
