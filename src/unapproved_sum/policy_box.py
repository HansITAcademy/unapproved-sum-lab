from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
import json
from typing import Iterable

from .models import ActionEvent, AgentDelegation


@dataclass(frozen=True)
class ApprovedWorkflow:
    workflow_id: str
    business_owner_role: str
    event_ids: tuple[str, ...]
    approved_edges: frozenset[tuple[str, str]]
    approval_status: str = "approved"
    approved_by_role: str = ""
    approved_by_actor: str = ""
    registry_version: str = "1.0"


@dataclass(frozen=True)
class ApprovalAttestation:
    role: str
    actor_id: str


@dataclass(frozen=True)
class PolicyDecision:
    decision_id: str
    description: str
    terminal_event_id: str
    required_states: frozenset[str]
    approval_paths: tuple[frozenset[str], ...]
    minimum_totals: tuple[tuple[str, float], ...] = ()
    minimum_distinct_approval_actors: int = 0
    source_record_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class BridgeCandidate:
    bridge_id: str
    edge: tuple[str, str]
    from_workflow_id: str
    to_workflow_id: str
    activation_states: frozenset[str]
    semantic_basis: str
    source_capability_ids: tuple[str, ...]


@dataclass(frozen=True)
class PolicyBox:
    box_id: str
    description: str
    workflows: tuple[ApprovedWorkflow, ...]
    events: tuple[ActionEvent, ...]
    delegations: dict[str, AgentDelegation]
    decisions: tuple[PolicyDecision, ...]
    bridge_candidates: tuple[BridgeCandidate, ...]
    baseline_delegated_decisions: frozenset[str]
    baseline_approval_attestations: tuple[ApprovalAttestation, ...]
    source_capability_ids: tuple[str, ...]

    @property
    def events_by_id(self) -> dict[str, ActionEvent]:
        return {event.event_id: event for event in self.events}

    @property
    def approved_edges(self) -> frozenset[tuple[str, str]]:
        return frozenset().union(*(workflow.approved_edges for workflow in self.workflows if workflow.approval_status == "approved"))

    @property
    def root_event_ids(self) -> tuple[str, ...]:
        incoming = {right for _, right in self.approved_edges}
        return tuple(
            workflow.event_ids[0]
            for workflow in self.workflows
            if workflow.event_ids and workflow.event_ids[0] not in incoming
        )


@dataclass(frozen=True)
class PathFinding:
    decision_id: str
    path: tuple[str, ...]
    path_edges: frozenset[tuple[str, str]]
    bridge_edges: frozenset[tuple[str, str]]
    states: frozenset[str]
    totals: tuple[tuple[str, float], ...]
    process_approved: bool
    decision_authorized: bool
    sod_satisfied: bool


@dataclass(frozen=True)
class PolicyBoxResult:
    condition: str
    active_bridges: tuple[tuple[str, str], ...]
    local_authorization_ok: bool
    owner_scope_ok: bool
    exact_owner_scope: bool
    component_audit_findings: tuple[str, ...]
    emergent_paths: tuple[tuple[str, ...], ...]
    compiled_decisions: tuple[str, ...]
    unauthorized_decisions: tuple[str, ...]
    unapproved_process_decisions: tuple[str, ...]
    sod_failures: tuple[str, ...]
    global_findings: tuple[str, ...]
    composition_only_findings: tuple[str, ...]
    uca: bool
    path_findings: tuple[PathFinding, ...]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_policy_box(path: Path | str = Path("scenarios/policy_box.json")) -> PolicyBox:
    path = Path(path)
    spec = _load_json(path)

    events = tuple(
        ActionEvent(
            event_id=item["event_id"],
            agent_id=item["agent_id"],
            action=item["action"],
            domain=item["domain"],
            consumes=frozenset(item.get("consumes", [])),
            produces=frozenset(item.get("produces", [])),
            quantitative_effects=tuple((x["key"], float(x["value"])) for x in item.get("quantitative_effects", [])),
        )
        for item in spec["events"]
    )

    delegations: dict[str, AgentDelegation] = {}
    for item in spec["delegations"]:
        owner_scope = frozenset(item["owner_allowed_actions"])
        agent_scope = frozenset(item.get("agent_allowed_actions", item["owner_allowed_actions"]))
        delegations[item["agent_id"]] = AgentDelegation(
            agent_id=item["agent_id"],
            owner_id=item["owner_id"],
            owner_role=item["owner_role"],
            owner_allowed_actions=owner_scope,
            agent_allowed_actions=agent_scope,
        )

    workflows = tuple(
        ApprovedWorkflow(
            workflow_id=item["workflow_id"],
            business_owner_role=item["business_owner_role"],
            event_ids=tuple(item["event_ids"]),
            approved_edges=frozenset(tuple(edge) for edge in item["approved_edges"]),
            approval_status=item.get("approval_status", "approved"),
            approved_by_role=item.get("approved_by_role", item["business_owner_role"]),
            approved_by_actor=item.get("approved_by_actor", ""),
            registry_version=item.get("registry_version", "1.0"),
        )
        for item in spec["approved_workflows"]
    )

    decisions = tuple(
        PolicyDecision(
            decision_id=item["decision_id"],
            description=item["description"],
            terminal_event_id=item["terminal_event_id"],
            required_states=frozenset(item.get("required_states", [])),
            approval_paths=tuple(frozenset(path_roles) for path_roles in item["approval_paths"]),
            minimum_totals=tuple((x["key"], float(x["minimum"])) for x in item.get("minimum_totals", [])),
            minimum_distinct_approval_actors=int(item.get("minimum_distinct_approval_actors", 0)),
            source_record_ids=tuple(item.get("source_record_ids", [])),
        )
        for item in spec["decision_policies"]
    )

    bridges = tuple(
        BridgeCandidate(
            bridge_id=item["bridge_id"],
            edge=tuple(item["edge"]),
            from_workflow_id=item["from_workflow_id"],
            to_workflow_id=item["to_workflow_id"],
            activation_states=frozenset(item.get("activation_states", [])),
            semantic_basis=item["semantic_basis"],
            source_capability_ids=tuple(item.get("source_capability_ids", [])),
        )
        for item in spec["bridge_candidates"]
    )

    attestations = tuple(
        ApprovalAttestation(role=item["role"], actor_id=item["actor_id"])
        for item in spec.get("baseline_approval_attestations", [])
    )

    return PolicyBox(
        box_id=spec["box_id"],
        description=spec["description"],
        workflows=workflows,
        events=events,
        delegations=delegations,
        decisions=decisions,
        bridge_candidates=bridges,
        baseline_delegated_decisions=frozenset(spec.get("baseline_delegated_decisions", [])),
        baseline_approval_attestations=attestations,
        source_capability_ids=tuple(spec.get("source_capability_ids", [])),
    )



def validate_policy_box(policy_box: PolicyBox) -> tuple[str, ...]:
    """Return structural validation errors for a frozen Policy Box.

    Validation is deliberately deterministic and independent of experimental outcomes.
    """
    errors: list[str] = []
    event_ids = [event.event_id for event in policy_box.events]
    if len(event_ids) != len(set(event_ids)):
        errors.append("duplicate_event_id")
    workflow_ids = [workflow.workflow_id for workflow in policy_box.workflows]
    if len(workflow_ids) != len(set(workflow_ids)):
        errors.append("duplicate_workflow_id")
    decision_ids = [decision.decision_id for decision in policy_box.decisions]
    if len(decision_ids) != len(set(decision_ids)):
        errors.append("duplicate_decision_id")

    known_events = set(event_ids)
    known_agents = set(policy_box.delegations)
    for event in policy_box.events:
        if event.agent_id not in known_agents:
            errors.append(f"event_missing_delegation:{event.event_id}")

    for workflow in policy_box.workflows:
        workflow_events = set(workflow.event_ids)
        if workflow.approval_status != "approved":
            errors.append(f"workflow_not_approved:{workflow.workflow_id}")
        if not workflow.approved_by_role or not workflow.approved_by_actor:
            errors.append(f"workflow_missing_approval_attestation:{workflow.workflow_id}")
        if not workflow.registry_version:
            errors.append(f"workflow_missing_registry_version:{workflow.workflow_id}")
        if not workflow_events:
            errors.append(f"empty_workflow:{workflow.workflow_id}")
        if not workflow_events.issubset(known_events):
            errors.append(f"workflow_unknown_event:{workflow.workflow_id}")
        for left, right in workflow.approved_edges:
            if left not in workflow_events or right not in workflow_events:
                errors.append(f"workflow_edge_outside_fragment:{workflow.workflow_id}:{left}->{right}")

    approved_edges = policy_box.approved_edges
    workflow_ids_set = set(workflow_ids)
    bridge_ids = [bridge.bridge_id for bridge in policy_box.bridge_candidates]
    if len(bridge_ids) != len(set(bridge_ids)):
        errors.append("duplicate_bridge_id")
    for bridge in policy_box.bridge_candidates:
        left, right = bridge.edge
        if bridge.from_workflow_id not in workflow_ids_set or bridge.to_workflow_id not in workflow_ids_set:
            errors.append(f"bridge_unknown_workflow:{bridge.bridge_id}")
        if bridge.from_workflow_id == bridge.to_workflow_id:
            errors.append(f"bridge_not_cross_workflow:{bridge.bridge_id}")
        if not bridge.activation_states:
            errors.append(f"bridge_missing_activation_state:{bridge.bridge_id}")
        if left not in known_events or right not in known_events:
            errors.append(f"bridge_unknown_event:{left}->{right}")
        if bridge.edge in approved_edges:
            errors.append(f"bridge_already_approved:{left}->{right}")
        if not bridge.source_capability_ids:
            errors.append(f"bridge_missing_source:{left}->{right}")

    for decision in policy_box.decisions:
        if decision.terminal_event_id not in known_events:
            errors.append(f"decision_unknown_terminal:{decision.decision_id}")
        if not decision.approval_paths:
            errors.append(f"decision_missing_approval_path:{decision.decision_id}")
        if not decision.source_record_ids:
            errors.append(f"decision_missing_policy_source:{decision.decision_id}")
        max_bundle = max((len(bundle) for bundle in decision.approval_paths), default=0)
        if decision.minimum_distinct_approval_actors > max_bundle:
            errors.append(f"decision_impossible_sod:{decision.decision_id}")

    return tuple(sorted(set(errors)))

def all_bridge_subsets(policy_box: PolicyBox) -> tuple[frozenset[tuple[str, str]], ...]:
    edges = tuple(candidate.edge for candidate in policy_box.bridge_candidates)
    subsets: list[frozenset[tuple[str, str]]] = []
    for size in range(len(edges) + 1):
        for subset in combinations(edges, size):
            subsets.append(frozenset(subset))
    return tuple(subsets)
