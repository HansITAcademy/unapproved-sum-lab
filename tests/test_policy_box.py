from __future__ import annotations

from pathlib import Path

from unapproved_sum.path_governance import all_simple_paths, evaluate_policy_box
from unapproved_sum.policy_box import ApprovalAttestation, all_bridge_subsets, load_policy_box


def test_policy_box_has_multiple_approved_workflows_and_bridges():
    box = load_policy_box()
    assert len(box.workflows) >= 5
    assert len(box.bridge_candidates) >= 4


def test_every_agent_exactly_matches_owner_scope():
    box = load_policy_box()
    assert all(d.exactly_matches_owner_scope for d in box.delegations.values())


def test_no_bridge_means_no_composition_decision():
    box = load_policy_box()
    result = evaluate_policy_box(box, condition="isolated", active_bridges=frozenset())
    assert result.emergent_paths == ()
    assert result.compiled_decisions == ()
    assert not result.uca


def test_disconnected_state_coexistence_does_not_compile_decision():
    box = load_policy_box()
    # All events exist in the box, but without bridge edges no cross-workflow decision may compile.
    result = evaluate_policy_box(box, condition="disconnected", active_bridges=frozenset())
    assert result.compiled_decisions == ()


def test_connected_full_bridge_replay_creates_multiple_new_workflows_and_uca():
    box = load_policy_box()
    bridges = frozenset(c.edge for c in box.bridge_candidates)
    result = evaluate_policy_box(box, condition="connected", active_bridges=bridges)
    assert result.local_authorization_ok
    assert result.owner_scope_ok
    assert result.exact_owner_scope
    assert len(result.emergent_paths) >= 4
    assert len(result.compiled_decisions) == 4
    assert len(result.unauthorized_decisions) == 4
    assert result.uca


def test_component_audit_passes_while_global_audit_finds_composition_only_issues():
    box = load_policy_box()
    bridges = frozenset(c.edge for c in box.bridge_candidates)
    result = evaluate_policy_box(box, condition="connected", active_bridges=bridges)
    assert result.component_audit_findings == ()
    assert result.global_findings
    assert set(result.composition_only_findings) == set(result.global_findings)


def test_process_approval_does_not_supply_decision_authority():
    box = load_policy_box()
    bridges = frozenset(c.edge for c in box.bridge_candidates)
    result = evaluate_policy_box(
        box,
        condition="process_only",
        active_bridges=bridges,
        approved_extra_edges=bridges,
    )
    assert result.unapproved_process_decisions == ()
    assert result.unauthorized_decisions
    assert result.uca


def test_decision_authority_does_not_approve_process():
    box = load_policy_box()
    bridges = frozenset(c.edge for c in box.bridge_candidates)
    decisions = frozenset(d.decision_id for d in box.decisions)
    approvals = (
        ApprovalAttestation("chief_procurement_officer", "cpo"),
        ApprovalAttestation("chief_compliance_officer", "cco"),
        ApprovalAttestation("chief_financial_officer", "cfo"),
        ApprovalAttestation("independent_compliance_reviewer", "reviewer"),
    )
    result = evaluate_policy_box(
        box,
        condition="authority_only",
        active_bridges=bridges,
        delegated_decisions=decisions,
        approval_attestations=approvals,
    )
    assert not result.unauthorized_decisions
    assert result.unapproved_process_decisions
    assert not result.uca


def test_roles_present_but_same_actor_fails_sod():
    box = load_policy_box()
    bridges = frozenset(c.edge for c in box.bridge_candidates)
    decisions = frozenset(d.decision_id for d in box.decisions)
    approvals = (
        ApprovalAttestation("chief_procurement_officer", "same"),
        ApprovalAttestation("chief_financial_officer", "same"),
        ApprovalAttestation("independent_compliance_reviewer", "same"),
        ApprovalAttestation("chief_compliance_officer", "cco"),
    )
    result = evaluate_policy_box(
        box,
        condition="sod_collapsed",
        active_bridges=bridges,
        approved_extra_edges=bridges,
        delegated_decisions=decisions,
        approval_attestations=approvals,
    )
    assert "cross_function_supplier_suspension_effect" in result.sod_failures
    assert "cross_function_supplier_suspension_effect" in result.unauthorized_decisions
    assert result.uca


def test_full_governance_resolves_uca_without_changing_local_scope():
    box = load_policy_box()
    bridges = frozenset(c.edge for c in box.bridge_candidates)
    decisions = frozenset(d.decision_id for d in box.decisions)
    approvals = (
        ApprovalAttestation("chief_procurement_officer", "cpo"),
        ApprovalAttestation("chief_compliance_officer", "cco"),
        ApprovalAttestation("chief_financial_officer", "cfo"),
        ApprovalAttestation("independent_compliance_reviewer", "reviewer"),
    )
    result = evaluate_policy_box(
        box,
        condition="governed",
        active_bridges=bridges,
        approved_extra_edges=bridges,
        delegated_decisions=decisions,
        approval_attestations=approvals,
    )
    assert result.local_authorization_ok and result.owner_scope_ok and result.exact_owner_scope
    assert result.unauthorized_decisions == ()
    assert result.unapproved_process_decisions == ()
    assert result.sod_failures == ()
    assert not result.uca


def test_threshold_decision_requires_bridge_and_aggregate_path_total():
    box = load_policy_box()
    result = evaluate_policy_box(box, condition="threshold", active_bridges=frozenset({("K", "L")}))
    assert "aggregate_related_commitment_over_90000" in result.compiled_decisions
    assert result.uca


def test_threshold_decision_not_triggered_when_fragments_disconnected():
    box = load_policy_box()
    result = evaluate_policy_box(box, condition="threshold_disconnected", active_bridges=frozenset())
    assert "aggregate_related_commitment_over_90000" not in result.compiled_decisions


def test_exhaustive_subsets_cover_all_combinations():
    box = load_policy_box()
    assert len(all_bridge_subsets(box)) == 2 ** len(box.bridge_candidates)


def test_decision_source_records_exist_in_authority_corpus():
    box = load_policy_box()
    import csv
    with Path("evidence/authority_corpus/decision_rights.csv").open(newline="", encoding="utf-8") as f:
        ids = {row["record_id"] for row in csv.DictReader(f)}
    for decision in box.decisions:
        assert decision.source_record_ids
        assert set(decision.source_record_ids).issubset(ids)


def test_missing_approvals_are_not_mislabeled_as_sod_failure():
    box = load_policy_box()
    bridges = frozenset(c.edge for c in box.bridge_candidates)
    result = evaluate_policy_box(box, condition="missing_approvals", active_bridges=bridges)
    assert "cross_function_supplier_suspension_effect" in result.unauthorized_decisions
    assert "cross_function_supplier_suspension_effect" not in result.sod_failures


def test_policy_box_structural_validation_passes():
    from unapproved_sum.policy_box import validate_policy_box

    box = load_policy_box()
    assert validate_policy_box(box) == ()


def test_baseline_workflows_have_explicit_approval_attestations_and_versions():
    box = load_policy_box()
    assert all(w.approval_status == "approved" for w in box.workflows)
    assert all(w.approved_by_role and w.approved_by_actor and w.registry_version for w in box.workflows)


def test_every_bridge_is_cross_workflow_and_has_activation_state():
    box = load_policy_box()
    assert all(b.from_workflow_id != b.to_workflow_id for b in box.bridge_candidates)
    assert all(b.activation_states for b in box.bridge_candidates)


def test_unknown_bridge_is_rejected():
    import pytest
    box = load_policy_box()
    with pytest.raises(ValueError):
        evaluate_policy_box(box, condition="bad", active_bridges=frozenset({("A", "F")}))


def test_bridge_semantics_are_not_just_graph_connectivity():
    from dataclasses import replace
    box = load_policy_box()
    # Make BR-01 require an impossible upstream state.  The graph remains connected,
    # but the semantic handoff must no longer produce the procurement decision.
    bridges = tuple(
        replace(b, activation_states=frozenset({"impossible_state"})) if b.edge == ("C", "X") else b
        for b in box.bridge_candidates
    )
    modified = replace(box, bridge_candidates=bridges)
    result = evaluate_policy_box(modified, condition="semantic_negative", active_bridges=frozenset({("C", "X")}))
    assert "supplier_procurement_suspension_effect" not in result.compiled_decisions


