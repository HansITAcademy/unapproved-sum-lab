from __future__ import annotations

import json
from pathlib import Path

from unapproved_sum.path_governance import evaluate_policy_box
from unapproved_sum.policy_box import ApprovalAttestation, load_policy_box


def serialize(result):
    return {
        "condition": result.condition,
        "active_bridges": [list(x) for x in result.active_bridges],
        "local_authorization_ok": result.local_authorization_ok,
        "owner_scope_ok": result.owner_scope_ok,
        "exact_owner_scope": result.exact_owner_scope,
        "component_audit_findings": list(result.component_audit_findings),
        "emergent_paths": [list(x) for x in result.emergent_paths],
        "compiled_decisions": list(result.compiled_decisions),
        "unauthorized_decisions": list(result.unauthorized_decisions),
        "unapproved_process_decisions": list(result.unapproved_process_decisions),
        "sod_failures": list(result.sod_failures),
        "global_findings": list(result.global_findings),
        "composition_only_findings": list(result.composition_only_findings),
        "uca": result.uca,
    }


def main():
    box = load_policy_box()
    all_bridges = frozenset(candidate.edge for candidate in box.bridge_candidates)
    all_decisions = frozenset(decision.decision_id for decision in box.decisions)
    all_approvals = (
        ApprovalAttestation("chief_procurement_officer", "actor_cpo"),
        ApprovalAttestation("chief_compliance_officer", "actor_cco"),
        ApprovalAttestation("chief_financial_officer", "actor_cfo"),
        ApprovalAttestation("independent_compliance_reviewer", "actor_independent"),
    )

    conditions = (
        evaluate_policy_box(box, condition="C0_rigid_baseline", active_bridges=frozenset()),
        evaluate_policy_box(box, condition="C1_isolated_agents", active_bridges=frozenset()),
        evaluate_policy_box(box, condition="C2_connected_bridge_replay", active_bridges=all_bridges),
        evaluate_policy_box(
            box,
            condition="C3_connected_process_approved_only",
            active_bridges=all_bridges,
            approved_extra_edges=all_bridges,
        ),
        evaluate_policy_box(
            box,
            condition="C4_connected_authority_only",
            active_bridges=all_bridges,
            delegated_decisions=all_decisions,
            approval_attestations=all_approvals,
        ),
        evaluate_policy_box(
            box,
            condition="C5_governed_connected",
            active_bridges=all_bridges,
            approved_extra_edges=all_bridges,
            delegated_decisions=all_decisions,
            approval_attestations=all_approvals,
        ),
    )

    print("=" * 154)
    print("PUBLICATION STUDY 3 — POLICY BOX: ISOLATED → CONNECTED → GOVERNED")
    print("=" * 154)
    print(f"{'CONDITION':38} {'BR':>3} {'PATHS':>5} {'DEC':>4} {'PROC':>4} {'UNAUTH':>6} {'SOD':>3} {'COMPONLY':>8} {'LOCAL':>5} {'OWNER':>5} {'UCA':>5}")
    print("-" * 154)
    for result in conditions:
        print(
            f"{result.condition:38} {len(result.active_bridges):>3} {len(result.emergent_paths):>5} "
            f"{len(result.compiled_decisions):>4} {len(result.unapproved_process_decisions):>4} "
            f"{len(result.unauthorized_decisions):>6} {len(result.sod_failures):>3} "
            f"{len(result.composition_only_findings):>8} {str(result.local_authorization_ok):>5} "
            f"{str(result.owner_scope_ok):>5} {str(result.uca):>5}"
        )

    connected = conditions[2]
    governed = conditions[5]
    assert connected.local_authorization_ok and connected.owner_scope_ok and connected.exact_owner_scope
    assert len(connected.emergent_paths) >= 4
    assert set(connected.compiled_decisions) == set(all_decisions)
    assert set(connected.unauthorized_decisions) == set(all_decisions)
    assert connected.uca
    assert connected.component_audit_findings == ()
    assert len(connected.composition_only_findings) > 0

    # Process approval alone leaves UCA; authority alone leaves process violations.
    assert conditions[3].uca and not conditions[3].unapproved_process_decisions
    assert not conditions[4].uca and conditions[4].unapproved_process_decisions

    # Full whole-workflow review resolves both dimensions without changing local scopes.
    assert not governed.uca
    assert governed.unapproved_process_decisions == ()
    assert governed.local_authorization_ok and governed.owner_scope_ok and governed.exact_owner_scope

    out = Path("results/policy_box_emergence_results.json")
    out.write_text(json.dumps({"policy_box": box.box_id, "conditions": [serialize(x) for x in conditions]}, indent=2), encoding="utf-8")

    print("\nCONNECTED CONDITION DECISIONS")
    for decision in connected.compiled_decisions:
        print("  ", decision)
    print("\nPOLICY BOX EMERGENCE: PASS")
    print("RESULTS SAVED:", out)


if __name__ == "__main__":
    main()
