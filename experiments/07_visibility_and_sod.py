from __future__ import annotations

import json
from pathlib import Path

from unapproved_sum.path_governance import evaluate_policy_box
from unapproved_sum.policy_box import ApprovalAttestation, load_policy_box


def main():
    box = load_policy_box()
    all_bridges = frozenset(candidate.edge for candidate in box.bridge_candidates)
    all_decisions = frozenset(decision.decision_id for decision in box.decisions)

    baseline = evaluate_policy_box(box, condition="connected", active_bridges=all_bridges)

    # All role names appear, but the joint-approval roles are collapsed onto one actor.
    same_actor_attestations = (
        ApprovalAttestation("chief_procurement_officer", "actor_shared"),
        ApprovalAttestation("chief_financial_officer", "actor_shared"),
        ApprovalAttestation("independent_compliance_reviewer", "actor_shared"),
        ApprovalAttestation("chief_compliance_officer", "actor_cco"),
    )
    collapsed_sod = evaluate_policy_box(
        box,
        condition="roles_present_same_actor",
        active_bridges=all_bridges,
        approved_extra_edges=all_bridges,
        delegated_decisions=all_decisions,
        approval_attestations=same_actor_attestations,
    )

    independent_attestations = (
        ApprovalAttestation("chief_procurement_officer", "actor_cpo"),
        ApprovalAttestation("chief_financial_officer", "actor_cfo"),
        ApprovalAttestation("independent_compliance_reviewer", "actor_review"),
        ApprovalAttestation("chief_compliance_officer", "actor_cco"),
    )
    full = evaluate_policy_box(
        box,
        condition="independent_approvals",
        active_bridges=all_bridges,
        approved_extra_edges=all_bridges,
        delegated_decisions=all_decisions,
        approval_attestations=independent_attestations,
    )

    assert baseline.component_audit_findings == ()
    assert len(baseline.global_findings) > 0
    assert set(baseline.composition_only_findings) == set(baseline.global_findings)

    assert "cross_function_supplier_suspension_effect" in collapsed_sod.sod_failures
    assert "cross_function_supplier_suspension_effect" in collapsed_sod.unauthorized_decisions
    assert collapsed_sod.uca

    assert full.sod_failures == ()
    assert full.unauthorized_decisions == ()
    assert not full.uca

    output = {
        "policy_box": box.box_id,
        "component_audit_findings": list(baseline.component_audit_findings),
        "global_findings": list(baseline.global_findings),
        "composition_only_findings": list(baseline.composition_only_findings),
        "visibility_gap_count": len(baseline.composition_only_findings),
        "collapsed_sod": {
            "sod_failures": list(collapsed_sod.sod_failures),
            "unauthorized_decisions": list(collapsed_sod.unauthorized_decisions),
            "uca": collapsed_sod.uca,
        },
        "independent_sod": {
            "sod_failures": list(full.sod_failures),
            "unauthorized_decisions": list(full.unauthorized_decisions),
            "uca": full.uca,
        },
    }
    out = Path("results/visibility_and_sod_results.json")
    out.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print("=" * 112)
    print("PUBLICATION STUDY 5 — COMPONENT VISIBILITY GAP + SEPARATION OF DUTIES")
    print("=" * 112)
    print("Component audit findings:", len(baseline.component_audit_findings))
    print("Global governance findings:", len(baseline.global_findings))
    print("Composition-only findings:", len(baseline.composition_only_findings))
    print("Collapsed-actor SoD failures:", collapsed_sod.sod_failures)
    print("Collapsed-actor UCA:", collapsed_sod.uca)
    print("Independent-actor SoD failures:", full.sod_failures)
    print("Independent-actor UCA:", full.uca)
    print("\nVISIBILITY + SOD: PASS")
    print("RESULTS SAVED:", out)


if __name__ == "__main__":
    main()
