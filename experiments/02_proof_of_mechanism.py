import json
from pathlib import Path

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


def main():
    errors = validate_case_grounding()
    assert not errors, errors

    print("=" * 150)
    print("PUBLICATION STUDY 1 — CORPUS-GROUNDED DETERMINISTIC PROOF")
    print("=" * 150)
    print(
        f"{'CASE':<34} {'PATTERN':<24} {'SOURCES':<18} "
        f"{'LOCAL':<7} {'OWNER':<7} {'DECISION':<38} {'UCA':<5}"
    )
    print("-" * 150)

    full_results = {}
    cut_results = {}
    export_rows = []

    for case_id in case_ids():
        scenario = load_grounded_scenario(case_id)
        full = evaluate(scenario)
        cut = evaluate(load_grounded_scenario(case_id, cut_last_event=True))
        full_results[case_id] = full
        cut_results[case_id] = cut

        print(
            f"{case_id:<34} {scenario.authority_pattern:<24} "
            f"{','.join(scenario.source_record_ids):<18} "
            f"{str(full.all_actions_locally_authorized):<7} "
            f"{str(full.all_agents_exactly_match_owner_scope):<7} "
            f"{(','.join(full.compiled_decisions) or '-'):<38} "
            f"{str(full.uca):<5}"
        )

        requirement = scenario.requirements[scenario.rules[0].decision_id]
        export_rows.append(
            {
                "case_id": case_id,
                "title": scenario.title,
                "authority_pattern": scenario.authority_pattern,
                "source_record_ids": list(scenario.source_record_ids),
                "grounding_note": scenario.grounding_note,
                "all_actions_locally_authorized": full.all_actions_locally_authorized,
                "all_agents_exactly_match_owner_scope": full.all_agents_exactly_match_owner_scope,
                "causal_edges": [list(edge) for edge in full.causal_edges],
                "compiled_decisions": list(full.compiled_decisions),
                "required_approval_paths": [sorted(path) for path in requirement.approval_paths],
                "workflow_delegated_decisions": sorted(scenario.authority.delegated_decisions),
                "workflow_approval_evidence": sorted(scenario.authority.approval_evidence),
                "uca": full.uca,
                "causal_cut_compiled_decisions": list(cut.compiled_decisions),
                "causal_cut_uca": cut.uca,
            }
        )

    for case_id, result in full_results.items():
        assert result.all_actions_locally_authorized, case_id
        assert result.all_agents_within_owner_scope, case_id
        assert result.all_agents_exactly_match_owner_scope, case_id
        assert result.uca, case_id
        assert result.unauthorized_compiled_decisions, case_id

    for case_id, result in cut_results.items():
        assert not result.compiled_decisions, case_id
        assert not result.uca, case_id

    print("\nCAUSAL-CUT NEGATIVE CONTROLS")
    for case_id, result in cut_results.items():
        print(
            f"  {case_id:<34} "
            f"DECISION={','.join(result.compiled_decisions) or '-':<10} UCA={result.uca}"
        )

    print("\nINTERPRETATION")
    print("- Every case is traced to one or more frozen civilian authority-corpus records.")
    print("- The source policies ground the authority topology; the agentic workflows are synthetic mechanism tests.")
    print("- Every executed action remains locally authorized and every agent exactly matches its owner's local scope.")
    print("- Composition nevertheless instantiates a policy-relevant decision for which the workflow lacks the required grant/approval bundle.")
    print("- Cutting the final causal link removes the compiled decision in every case.")

    output = Path("results/corpus_grounded_mechanism_results.json")
    output.write_text(json.dumps({"cases": export_rows}, indent=2) + "\n", encoding="utf-8")
    print(f"RESULTS SAVED: {output}")


if __name__ == "__main__":
    main()
