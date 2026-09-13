from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Tuple


@dataclass(frozen=True)
class AgentDelegation:
    """Local delegation from a human/organizational owner to an agent."""

    agent_id: str
    owner_id: str
    owner_role: str
    owner_allowed_actions: FrozenSet[str]
    agent_allowed_actions: FrozenSet[str]

    @property
    def exceeds_owner_scope(self) -> bool:
        return not self.agent_allowed_actions.issubset(self.owner_allowed_actions)

    @property
    def exactly_matches_owner_scope(self) -> bool:
        return self.agent_allowed_actions == self.owner_allowed_actions


@dataclass(frozen=True)
class ActionEvent:
    """One locally executed action and the state/effects it produces."""

    event_id: str
    agent_id: str
    action: str
    domain: str
    consumes: FrozenSet[str]
    produces: FrozenSet[str]
    quantitative_effects: Tuple[Tuple[str, float], ...] = ()


@dataclass(frozen=True)
class DecisionRule:
    """Institutional semantics for when combined state/effects amount to a decision.

    `minimum_totals` is optional and supports threshold-grounded cases without
    introducing a universal authority ladder. Each pair is (effect_key, minimum).
    """

    decision_id: str
    description: str
    required_state: FrozenSet[str]
    minimum_totals: Tuple[Tuple[str, float], ...] = ()


@dataclass(frozen=True)
class DecisionRequirement:
    """Policy requirement for an institutional decision.

    `approval_paths` are alternative valid approval bundles. Each bundle is a
    conjunction: every role in the bundle is required. Multiple bundles encode
    alternative valid paths.
    """

    decision_id: str
    approval_paths: Tuple[FrozenSet[str], ...]


@dataclass(frozen=True)
class WorkflowAuthority:
    """What the institution explicitly approved/delegated to the workflow itself."""

    workflow_id: str
    delegated_decisions: FrozenSet[str]
    approval_evidence: FrozenSet[str]
    approved_edges: FrozenSet[Tuple[str, str]]


@dataclass(frozen=True)
class EvaluationResult:
    workflow_id: str
    all_actions_locally_authorized: bool
    all_agents_within_owner_scope: bool
    all_agents_exactly_match_owner_scope: bool
    local_authorization_violations: Tuple[str, ...]
    owner_scope_violations: Tuple[str, ...]
    causal_edges: Tuple[Tuple[str, str], ...]
    unapproved_edges: Tuple[Tuple[str, str], ...]
    compiled_decisions: Tuple[str, ...]
    unauthorized_compiled_decisions: Tuple[str, ...]
    unapproved_composition: bool
    uca: bool
