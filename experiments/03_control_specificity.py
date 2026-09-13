import json
from pathlib import Path

from unapproved_sum.evaluation import evaluate_workflow
from unapproved_sum.scenarios import case_ids, load_grounded_scenario


def evaluate(scenario):
    return evaluate_workflow(
        events=scenario.events,
        delegations=scenario.delegations,
        decision_rules=scenario.rules,
        decision_requirements=scenario.requirements,
        workflow_authority=scenario.authority,
    )


def main():
    print("=" * 132)
    print("PUBLICATION STUDY 2 — PROCESS APPROVAL VS DECISION AUTHORITY")
    print("=" * 132)
    print(f"{'CASE':<34} {'CONDITION':<36} {'UNAPPROVED PROCESS':<20} {'UCA':<6}")
    print("-" * 132)

    export_rows = []

    for case_id in case_ids():
        conditions = {
            "unapproved_process_insufficient_authority": load_grounded_scenario(
                case_id,
                approve_full_workflow=False,
            ),
            "approved_process_insufficient_authority": load_grounded_scenario(
                case_id,
                approve_full_workflow=True,
            ),
            "unapproved_process_sufficient_authority": load_grounded_scenario(
                case_id,
                approve_full_workflow=False,
                grant_required_decision=True,
                include_required_approvals=True,
            ),
            "approved_process_sufficient_authority": load_grounded_scenario(
                case_id,
                approve_full_workflow=True,
                grant_required_decision=True,
                include_required_approvals=True,
            ),
        }

        results = {name: evaluate(scenario) for name, scenario in conditions.items()}

        for name, result in results.items():
            print(
                f"{case_id:<34} {name:<36} "
                f"{str(result.unapproved_composition):<20} {str(result.uca):<6}"
            )
            export_rows.append(
                {
                    "case_id": case_id,
                    "condition": name,
                    "unapproved_composition": result.unapproved_composition,
                    "uca": result.uca,
                    "compiled_decisions": list(result.compiled_decisions),
                    "unauthorized_compiled_decisions": list(result.unauthorized_compiled_decisions),
                }
            )

        assert results["unapproved_process_insufficient_authority"].unapproved_composition
        assert results["unapproved_process_insufficient_authority"].uca

        assert not results["approved_process_insufficient_authority"].unapproved_composition
        assert results["approved_process_insufficient_authority"].uca

        assert results["unapproved_process_sufficient_authority"].unapproved_composition
        assert not results["unapproved_process_sufficient_authority"].uca

        assert not results["approved_process_sufficient_authority"].unapproved_composition
        assert not results["approved_process_sufficient_authority"].uca

    print("\nPASS: workflow approval and decision authority remain separable across all four corpus-grounded authority structures.")
    output = Path("results/control_specificity_results.json")
    output.write_text(json.dumps({"runs": export_rows}, indent=2) + "\n", encoding="utf-8")
    print(f"RESULTS SAVED: {output}")


if __name__ == "__main__":
    main()
