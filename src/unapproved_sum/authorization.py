from __future__ import annotations

from collections.abc import Iterable, Mapping

from .models import ActionEvent, AgentDelegation, DecisionRequirement, WorkflowAuthority


def local_authorization_violations(
    events: Iterable[ActionEvent],
    delegations: Mapping[str, AgentDelegation],
) -> tuple[str, ...]:
    violations: list[str] = []
    for event in events:
        delegation = delegations.get(event.agent_id)
        if delegation is None:
            violations.append(f"{event.event_id}:missing_delegation")
            continue
        if event.action not in delegation.agent_allowed_actions:
            violations.append(f"{event.event_id}:action_not_locally_authorized")
    return tuple(violations)


def owner_scope_violations(
    delegations: Mapping[str, AgentDelegation],
) -> tuple[str, ...]:
    return tuple(
        delegation.agent_id
        for delegation in delegations.values()
        if delegation.exceeds_owner_scope
    )


def decision_is_authorized(
    decision_id: str,
    requirement: DecisionRequirement,
    authority: WorkflowAuthority,
) -> bool:
    """A composed decision needs workflow-level delegation AND policy approvals.

    Local agent/owner grants are deliberately not unioned here. This is the core
    non-composition principle: local decision rights do not automatically become
    an end-to-end workflow decision-right.
    """

    if decision_id not in authority.delegated_decisions:
        return False

    return any(
        approval_path.issubset(authority.approval_evidence)
        for approval_path in requirement.approval_paths
    )
