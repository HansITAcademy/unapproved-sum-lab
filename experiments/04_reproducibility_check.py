from unapproved_sum.evaluation import evaluate_workflow
from unapproved_sum.scenarios import case_ids, load_grounded_scenario, validate_case_grounding


def fingerprint(result):
    return (
        result.all_actions_locally_authorized,
        result.all_agents_within_owner_scope,
        result.all_agents_exactly_match_owner_scope,
        result.causal_edges,
        result.unapproved_edges,
        result.compiled_decisions,
        result.unauthorized_compiled_decisions,
        result.uca,
    )


def run(scenario):
    return evaluate_workflow(
        events=scenario.events,
        delegations=scenario.delegations,
        decision_rules=scenario.rules,
        decision_requirements=scenario.requirements,
        workflow_authority=scenario.authority,
    )


def main():
    errors = validate_case_grounding()
    assert not errors, errors

    for case_id in case_ids():
        first = fingerprint(run(load_grounded_scenario(case_id)))
        second = fingerprint(run(load_grounded_scenario(case_id)))
        assert first == second, case_id

    print("REPRODUCIBILITY CHECK: PASS")


if __name__ == "__main__":
    main()
