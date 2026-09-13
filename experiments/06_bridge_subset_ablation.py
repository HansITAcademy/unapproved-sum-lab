from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from unapproved_sum.path_governance import evaluate_policy_box
from unapproved_sum.policy_box import all_bridge_subsets, load_policy_box


def main():
    box = load_policy_box()
    rows = []
    sufficient_sets: dict[str, list[tuple[tuple[str, str], ...]]] = defaultdict(list)

    for subset in all_bridge_subsets(box):
        result = evaluate_policy_box(box, condition="subset", active_bridges=subset)
        row = {
            "bridges": [list(x) for x in sorted(subset)],
            "bridge_count": len(subset),
            "emergent_path_count": len(result.emergent_paths),
            "compiled_decisions": list(result.compiled_decisions),
            "unauthorized_decisions": list(result.unauthorized_decisions),
            "uca": result.uca,
        }
        rows.append(row)
        for decision_id in result.compiled_decisions:
            sufficient_sets[decision_id].append(tuple(sorted(subset)))

    minimal: dict[str, list[list[list[str]]]] = {}
    for decision_id, sets_ in sufficient_sets.items():
        mins = []
        for candidate in sets_:
            cset = set(candidate)
            if not any(set(other) < cset for other in sets_):
                mins.append(candidate)
        minimal[decision_id] = [[list(edge) for edge in candidate] for candidate in sorted(set(mins))]

    # Structural assertions.
    empty = next(row for row in rows if row["bridge_count"] == 0)
    full = max(rows, key=lambda row: row["bridge_count"])
    assert empty["compiled_decisions"] == [] and not empty["uca"]
    assert len(full["compiled_decisions"]) == len(box.decisions) and full["uca"]

    # Each policy decision must have at least one minimal bridge set; the threshold decision
    # must depend on the commitment bridge specifically.
    assert set(minimal) == {decision.decision_id for decision in box.decisions}
    threshold_sets = minimal["aggregate_related_commitment_over_90000"]
    assert threshold_sets == [[["K", "L"]]], threshold_sets

    out = Path("results/bridge_subset_ablation_results.json")
    out.write_text(json.dumps({"policy_box": box.box_id, "subset_count": len(rows), "rows": rows, "minimal_bridge_sets": minimal}, indent=2), encoding="utf-8")

    print("=" * 112)
    print("PUBLICATION STUDY 4 — EXHAUSTIVE BRIDGE-SUBSET ABLATION")
    print("=" * 112)
    print(f"Candidate bridges: {len(box.bridge_candidates)}")
    print(f"Exhaustive subsets tested: {len(rows)}")
    print(f"No-bridge compiled decisions: {len(empty['compiled_decisions'])}")
    print(f"Full-bridge compiled decisions: {len(full['compiled_decisions'])}")
    print("\nMINIMAL BRIDGE SETS")
    for decision_id in sorted(minimal):
        print(f"  {decision_id}")
        for bridge_set in minimal[decision_id]:
            print("    ", bridge_set)
    print("\nBRIDGE-SUBSET ABLATION: PASS")
    print("RESULTS SAVED:", out)


if __name__ == "__main__":
    main()
