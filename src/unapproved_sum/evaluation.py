from __future__ import annotations

from collections.abc import Iterable, Mapping

from .authorization import (
    decision_is_authorized,
    local_authorization_violations,
    owner_scope_violations,
)
from .composition import causal_edges, compiled_decisions
from .models import (
    ActionEvent,
    AgentDelegation,
    DecisionRequirement,
    DecisionRule,
    EvaluationResult,
    WorkflowAuthority,
)


def evaluate_workflow(
    *,
    events: Iterable[ActionEvent],
    delegations: Mapping[str, AgentDelegation],
    decision_rules: Iterable[DecisionRule],
    decision_requirements: Mapping[str, DecisionRequirement],
    workflow_authority: WorkflowAuthority,
) -> EvaluationResult:
    events = tuple(events)
    rules = tuple(decision_rules)

    local_violations = local_authorization_violations(events, delegations)
    owner_violations = owner_scope_violations(delegations)
    edges = causal_edges(events)
    unapproved = tuple(edge for edge in edges if edge not in workflow_authority.approved_edges)
    decisions = compiled_decisions(events, rules)

    unauthorized: list[str] = []
    for decision_id in decisions:
        requirement = decision_requirements[decision_id]
        if not decision_is_authorized(decision_id, requirement, workflow_authority):
            unauthorized.append(decision_id)

    local_ok = not local_violations
    owner_ok = not owner_violations

    # UCA is intentionally reserved for the clean composition case. If an agent
    # itself exceeds local/owner authority, that is an ordinary authorization failure.
    uca = local_ok and owner_ok and bool(unauthorized)

    return EvaluationResult(
        workflow_id=workflow_authority.workflow_id,
        all_actions_locally_authorized=local_ok,
        all_agents_within_owner_scope=owner_ok,
        all_agents_exactly_match_owner_scope=all(
            delegation.exactly_matches_owner_scope
            for delegation in delegations.values()
        ),
        local_authorization_violations=local_violations,
        owner_scope_violations=owner_violations,
        causal_edges=edges,
        unapproved_edges=unapproved,
        compiled_decisions=decisions,
        unauthorized_compiled_decisions=tuple(unauthorized),
        unapproved_composition=bool(unapproved),
        uca=uca,
    )
