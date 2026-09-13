from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

from .authority_corpus import load_records
from .models import (
    ActionEvent,
    AgentDelegation,
    DecisionRequirement,
    DecisionRule,
    WorkflowAuthority,
)

DEFAULT_CASES_PATH = Path("scenarios/grounded_cases.json")


@dataclass(frozen=True)
class Scenario:
    case_id: str
    title: str
    authority_pattern: str
    source_record_ids: tuple[str, ...]
    grounding_note: str
    events: tuple[ActionEvent, ...]
    delegations: dict[str, AgentDelegation]
    rules: tuple[DecisionRule, ...]
    requirements: dict[str, DecisionRequirement]
    authority: WorkflowAuthority


def _load_specs(path: Path = DEFAULT_CASES_PATH) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["cases"]


def case_ids(path: Path = DEFAULT_CASES_PATH) -> tuple[str, ...]:
    return tuple(case["case_id"] for case in _load_specs(path))


def _delegation(spec: dict) -> AgentDelegation:
    owner_scope = frozenset(spec["owner_allowed_actions"])
    agent_scope = frozenset(spec.get("agent_allowed_actions", spec["owner_allowed_actions"]))
    return AgentDelegation(
        agent_id=spec["agent_id"],
        owner_id=spec["owner_id"],
        owner_role=spec["owner_role"],
        owner_allowed_actions=owner_scope,
        agent_allowed_actions=agent_scope,
    )


def _event(spec: dict) -> ActionEvent:
    return ActionEvent(
        event_id=spec["event_id"],
        agent_id=spec["agent_id"],
        action=spec["action"],
        domain=spec["domain"],
        consumes=frozenset(spec.get("consumes", [])),
        produces=frozenset(spec.get("produces", [])),
        quantitative_effects=tuple(
            (item["key"], float(item["value"]))
            for item in spec.get("quantitative_effects", [])
        ),
    )


def _rule(spec: dict) -> DecisionRule:
    return DecisionRule(
        decision_id=spec["decision_id"],
        description=spec["description"],
        required_state=frozenset(spec.get("required_state", [])),
        minimum_totals=tuple(
            (item["key"], float(item["minimum"]))
            for item in spec.get("minimum_totals", [])
        ),
    )


def load_grounded_scenario(
    case_id: str,
    *,
    approve_full_workflow: bool = True,
    grant_required_decision: bool = False,
    include_required_approvals: bool = False,
    cut_last_event: bool = False,
    path: Path = DEFAULT_CASES_PATH,
) -> Scenario:
    specs = {case["case_id"]: case for case in _load_specs(path)}
    if case_id not in specs:
        raise KeyError(f"Unknown corpus-grounded case: {case_id}")

    spec = specs[case_id]
    rule = _rule(spec["decision_rule"])
    requirement = DecisionRequirement(
        decision_id=rule.decision_id,
        approval_paths=tuple(
            frozenset(path_roles) for path_roles in spec["required_approval_paths"]
        ),
    )

    events = tuple(_event(event) for event in spec["events"])
    if cut_last_event:
        events = events[:-1]

    delegations = {
        item["agent_id"]: _delegation(item)
        for item in spec["delegations"]
    }

    all_edges = frozenset(tuple(edge) for edge in spec["full_workflow_edges"])
    approved_edges = all_edges if approve_full_workflow else frozenset(
        tuple(edge) for edge in spec["partial_workflow_edges"]
    )

    delegated_decisions = set(spec["baseline_delegated_decisions"])
    approval_evidence = set(spec["baseline_approval_evidence"])

    if grant_required_decision:
        delegated_decisions.add(rule.decision_id)
    if include_required_approvals:
        approval_evidence.update(
            role
            for approval_path in spec["required_approval_paths"]
            for role in approval_path
        )

    return Scenario(
        case_id=spec["case_id"],
        title=spec["title"],
        authority_pattern=spec["authority_pattern"],
        source_record_ids=tuple(spec["source_record_ids"]),
        grounding_note=spec["grounding_note"],
        events=events,
        delegations=delegations,
        rules=(rule,),
        requirements={rule.decision_id: requirement},
        authority=WorkflowAuthority(
            workflow_id=spec["workflow_id"],
            delegated_decisions=frozenset(delegated_decisions),
            approval_evidence=frozenset(approval_evidence),
            approved_edges=approved_edges,
        ),
    )


def validate_case_grounding(path: Path = DEFAULT_CASES_PATH) -> list[str]:
    """Validate that every experimental case traces to the frozen authority corpus."""

    errors: list[str] = []
    records = {record.record_id: record for record in load_records()}

    for spec in _load_specs(path):
        if not spec.get("source_record_ids"):
            errors.append(f"{spec['case_id']}:missing_source_records")
            continue

        source_patterns: set[str] = set()
        for record_id in spec["source_record_ids"]:
            if record_id not in records:
                errors.append(f"{spec['case_id']}:missing_corpus_record:{record_id}")
                continue
            source_patterns.add(records[record_id].authority_pattern)

        expected = set(spec["grounded_patterns"])
        if not expected.issubset(source_patterns):
            errors.append(
                f"{spec['case_id']}:pattern_mismatch:expected={sorted(expected)}:found={sorted(source_patterns)}"
            )

        if not spec.get("abstraction_disclaimer"):
            errors.append(f"{spec['case_id']}:missing_abstraction_disclaimer")

    return errors
