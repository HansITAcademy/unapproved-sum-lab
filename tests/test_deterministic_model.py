from unapproved_sum.evaluation import evaluate_workflow
from unapproved_sum.scenarios import case_ids, load_grounded_scenario, validate_case_grounding


def evaluate(scenario):
    return evaluate_workflow(
        events=scenario.events,
        delegations=scenario.delegations,
        decision_rules=scenario.rules,
        decision_requirements=scenario.requirements,
        workflow_authority=scenario.authority,
    )


def test_four_grounded_cases_exist():
    assert case_ids() == (
        "CG-01-PROPOSAL-DECISION-SPLIT",
        "CG-02-THRESHOLD-ESCALATION",
        "CG-03-RESERVED-ROLE",
        "CG-04-JOINT-APPROVAL",
    )


def test_grounded_cases_trace_to_frozen_corpus():
    assert validate_case_grounding() == []


def test_all_agents_exactly_match_owner_local_scope():
    for case_id in case_ids():
        scenario = load_grounded_scenario(case_id)
        assert all(d.exactly_matches_owner_scope for d in scenario.delegations.values())


def test_all_four_grounded_cases_demonstrate_pure_uca():
    for case_id in case_ids():
        result = evaluate(load_grounded_scenario(case_id))
        assert result.all_actions_locally_authorized, case_id
        assert result.all_agents_within_owner_scope, case_id
        assert result.all_agents_exactly_match_owner_scope, case_id
        assert result.uca, case_id
        assert result.unauthorized_compiled_decisions, case_id


def test_causal_cut_removes_compiled_decision_in_every_case():
    for case_id in case_ids():
        result = evaluate(load_grounded_scenario(case_id, cut_last_event=True))
        assert result.compiled_decisions == (), case_id
        assert not result.uca, case_id


def test_full_decision_grant_and_required_approvals_remove_uca():
    for case_id in case_ids():
        result = evaluate(
            load_grounded_scenario(
                case_id,
                grant_required_decision=True,
                include_required_approvals=True,
            )
        )
        assert not result.uca, case_id


def test_workflow_approval_does_not_grant_decision_authority():
    for case_id in case_ids():
        result = evaluate(load_grounded_scenario(case_id, approve_full_workflow=True))
        assert not result.unapproved_composition, case_id
        assert result.uca, case_id


def test_decision_authority_does_not_approve_workflow_topology():
    for case_id in case_ids():
        result = evaluate(
            load_grounded_scenario(
                case_id,
                approve_full_workflow=False,
                grant_required_decision=True,
                include_required_approvals=True,
            )
        )
        assert result.unapproved_composition, case_id
        assert not result.uca, case_id


def test_full_workflow_edges_match_inferred_causal_edges():
    for case_id in case_ids():
        scenario = load_grounded_scenario(case_id)
        result = evaluate(scenario)
        assert frozenset(result.causal_edges) == scenario.authority.approved_edges, case_id


def test_threshold_case_requires_secretarial_level_approval():
    scenario = load_grounded_scenario("CG-02-THRESHOLD-ESCALATION")
    requirement = scenario.requirements["aggregate_obligation_over_90000_effect"]
    assert requirement.approval_paths == (frozenset({"secretarial_level"}),)


def test_joint_case_requires_complete_four_role_bundle_and_baseline_omits_final_role():
    scenario = load_grounded_scenario("CG-04-JOINT-APPROVAL")
    requirement = scenario.requirements["high_value_award_effect"]
    required = frozenset(
        {
            "chief_operating_officer",
            "department_of_treasury",
            "opm",
            "president",
        }
    )
    assert requirement.approval_paths == (required,)
    assert "president" not in scenario.authority.approval_evidence


def test_approval_bundle_without_explicit_decision_grant_is_still_insufficient():
    for case_id in case_ids():
        scenario = load_grounded_scenario(
            case_id,
            grant_required_decision=False,
            include_required_approvals=True,
        )
        result = evaluate(scenario)
        assert result.uca, case_id
