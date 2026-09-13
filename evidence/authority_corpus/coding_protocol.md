# External Authority Corpus — Coding Protocol

## Purpose

This corpus grounds the publication model in **documented civilian institutional decision-right structures**.

The corpus is not a prevalence estimate and does not claim that every organization uses the same authority model. Its purpose is narrower: establish that real institutions formally distinguish local action rights from final decision authority and use structures such as reserved authority, approval prerequisites, thresholds, nonredelegable grants, proposal/decision separation, and multi-role approval chains.

Department of Defense and military sources are excluded.

## Unit of analysis

One row represents one distinct documented decision-right or authority boundary.

A row should be coded only when an official primary source identifies:

1. an actor or role that may take some action;
2. the institutional decision or effect at issue; and
3. a condition, role, approval, threshold, or other rule governing who may make the decision.

## Fields

- `record_id`: stable corpus identifier.
- `source_id`: foreign key into `sources.json`.
- `organization`: institution named by the source.
- `domain`: functional area.
- `decision`: institutional decision being governed.
- `local_actor`: actor performing the local or precursor action.
- `local_right`: what the local actor is actually allowed to do.
- `required_authority`: role or approval bundle required for the governed decision.
- `authority_pattern`: normalized authority structure.
- `threshold_or_condition`: policy condition that activates the authority rule.
- `redelegation`: whether the authority may be passed onward.
- `finality`: whether the coded act is local, intermediate, final, review, or mixed.
- `source_locator`: section/table locator.
- `support_summary`: paraphrase of the relevant source support.
- `verification_status`: source-verification state.

## Allowed authority patterns

- `bounded_delegation`: authority exists only within an explicit delegated scope.
- `approval_prerequisite`: a decision requires additional clearances/approvals before it becomes valid.
- `reserved_role`: the final decision is reserved to a specified role/body.
- `threshold_escalation`: the required decision-maker changes when a threshold is crossed.
- `proposal_decision_split`: one actor may propose/recommend while another holds the final decision-right.
- `nonredelegable_grant`: the policy expressly prevents onward delegation.
- `joint_approval`: multiple distinct institutional approvals are required for one decision.
- `multi_role_chain`: different roles hold sequentially necessary authorities in one institutional process.
- `review_override`: a reviewing body can reopen, revise, or supersede another decision.

## Coding rules

1. Use official civilian primary sources only.
2. Exclude Department of Defense and military sources.
3. Paraphrase support; do not convert ambiguous language into a stronger authority claim.
4. Do not force authority into a universal numeric hierarchy.
5. Preserve conjunctions. If a decision needs A + B + C, code the full bundle.
6. Preserve thresholds as thresholds.
7. Preserve proposal/recommendation authority separately from final decision authority.
8. Preserve nonredelegation and review/override rules.
9. If the policy is ambiguous, exclude the row or mark it for review rather than guessing.
10. The corpus demonstrates existence and structure, not prevalence or frequency.

## Quality controls

The repository validator checks:

- unique record IDs;
- valid source foreign keys;
- official `.gov` source URLs;
- excluded defense/military terms;
- valid authority-pattern vocabulary;
- required fields;
- source utilization; and
- basic diversity/minimum-size criteria in the analysis script.

The final publication should report the corpus selection rule and the fact that records were purposefully sampled to cover distinct authority structures.
