from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from unapproved_sum.authority_corpus import (
    load_records,
    load_sources,
    summarize_corpus,
    validate_corpus,
)


def main() -> None:
    records = load_records()
    sources = load_sources()
    errors = validate_corpus(records, sources)
    summary = summarize_corpus(records, sources)

    pattern_orgs: dict[str, set[str]] = {}
    for record in records:
        pattern_orgs.setdefault(record.authority_pattern, set()).add(record.organization)

    checks = {
        "corpus_validation": not errors,
        "at_least_40_records": summary["records"] >= 40,
        "at_least_15_sources": summary["sources"] >= 15,
        "at_least_8_organizations": summary["organizations"] >= 8,
        "at_least_8_domains": summary["domains"] >= 8,
        "all_sources_official_primary": all(
            source.official_primary_source for source in sources.values()
        ),
        "no_defense_or_military_sources": not any(
            "excluded_defense_term" in error for error in errors
        ),
        "core_patterns_present": {
            "bounded_delegation",
            "reserved_role",
            "threshold_escalation",
            "proposal_decision_split",
            "nonredelegable_grant",
            "joint_approval",
            "multi_role_chain",
        }.issubset(summary["patterns"]),
        "proposal_decision_split_multi_org": len(
            pattern_orgs.get("proposal_decision_split", set())
        ) >= 4,
        "threshold_escalation_multi_org": len(
            pattern_orgs.get("threshold_escalation", set())
        ) >= 3,
        "reserved_role_multi_org": len(
            pattern_orgs.get("reserved_role", set())
        ) >= 5,
        "joint_or_multi_role_evidence_present": summary["joint_or_multi_role_records"] >= 3,
        "no_single_source_dominates": summary["max_source_share"] <= 0.25,
        "no_single_organization_dominates": summary["max_organization_share"] <= 0.30,
    }

    print("=" * 92)
    print("STUDY 0 — EXTERNAL CIVILIAN AUTHORITY CORPUS")
    print("=" * 92)
    print(f"Records:       {summary['records']}")
    print(f"Sources:       {summary['sources']}")
    print(f"Organizations: {summary['organizations']}")
    print(f"Domains:       {summary['domains']}")
    print()

    print("AUTHORITY PATTERNS")
    for pattern, count in summary["patterns"].items():
        print(f"  {pattern:<26} {count}")

    print()
    print("QUALITY CHECKS")
    for name, passed in checks.items():
        print(f"  {name:<44} {'PASS' if passed else 'FAIL'}")

    if errors:
        print()
        print("VALIDATION ERRORS")
        for error in errors:
            print(f"  - {error}")

    output = {
        "summary": summary,
        "pattern_organizations": {
            key: sorted(value) for key, value in sorted(pattern_orgs.items())
        },
        "checks": checks,
        "validation_errors": errors,
        "interpretation": (
            "The corpus demonstrates the existence of policy-relative authority "
            "structures in civilian institutions. It is not a prevalence estimate of UCA."
        ),
    }

    Path("results").mkdir(exist_ok=True)
    Path("results/authority_corpus_summary.json").write_text(
        json.dumps(output, indent=2) + "\n",
        encoding="utf-8",
    )

    if not all(checks.values()):
        raise SystemExit("AUTHORITY CORPUS ANALYSIS: FAIL")

    print()
    print("AUTHORITY CORPUS ANALYSIS: PASS")
    print("SUMMARY SAVED: results/authority_corpus_summary.json")


if __name__ == "__main__":
    main()
