from unapproved_sum.composition import accumulated_totals, causal_edges, compiled_decisions
from unapproved_sum.scenarios import load_grounded_scenario


def test_causal_edges_require_state_dependency():
    scenario = load_grounded_scenario("CG-01-PROPOSAL-DECISION-SPLIT")
    assert causal_edges(scenario.events) == (
        ("proposal_notice", "interim_restriction"),
        ("interim_restriction", "status_record"),
    )


def test_compiled_decision_depends_on_joint_state():
    full = load_grounded_scenario("CG-01-PROPOSAL-DECISION-SPLIT")
    cut = load_grounded_scenario(
        "CG-01-PROPOSAL-DECISION-SPLIT",
        cut_last_event=True,
    )
    assert compiled_decisions(full.events, full.rules) == ("final_adverse_action_effect",)
    assert compiled_decisions(cut.events, cut.rules) == ()


def test_threshold_case_uses_aggregate_quantitative_effect():
    full = load_grounded_scenario("CG-02-THRESHOLD-ESCALATION")
    cut = load_grounded_scenario("CG-02-THRESHOLD-ESCALATION", cut_last_event=True)

    assert accumulated_totals(full.events)["obligation_usd"] == 100000.0
    assert accumulated_totals(cut.events)["obligation_usd"] == 50000.0
    assert compiled_decisions(full.events, full.rules) == (
        "aggregate_obligation_over_90000_effect",
    )
    assert compiled_decisions(cut.events, cut.rules) == ()
