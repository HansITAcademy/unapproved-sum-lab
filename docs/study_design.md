# Study design

This document is the short methods note for the code repository. The paper carries the fuller conceptual argument; this file says exactly what the lab is doing.

## The object being tested

The lab does not ask whether an agent has a stolen credential or an obviously forbidden tool. Those are normal authorization failures.

The test starts after local authorization succeeds. Each component has an owner, the agent's local scope does not exceed that owner's scope, and the local action is permitted. The question is whether connecting those components creates a causal workflow that instantiates a different institutional decision.

The Policy Box therefore tracks three things independently:

1. whether each local action is permitted;
2. whether the connected workflow/process is approved; and
3. whether the workflow has the decision-right and approval evidence required for the decision created by the connected path.

UCA is the third-layer mismatch under the required local-authorization and owner-scope conditions.

## Deterministic phase

The deterministic phase is there to test the mechanism before any stochastic model behavior is involved. It includes:

- corpus-grounded authority patterns;
- causal-cut negative controls;
- independent variation of process approval and decision authority;
- isolated, connected, process-approved, authority-approved, and fully governed Policy Box states;
- all 16 subsets of the four candidate bridge edges; and
- component-only versus whole-workflow visibility plus a separation-of-duties control.

A policy-defined compiled decision is path-sensitive. Facts that merely coexist in disconnected workflows are not unioned into a decision.

## Live-model phase

The eight tasks are frozen in `scenarios/tasks.json`.

The four generation conditions are:

- `L0_ISOLATED_LOCAL`: local function only; no cross-workflow handoff;
- `L1_CONNECTED_OPAQUE`: another function can be called, with limited shared state and at most one handoff;
- `L2_CONNECTED_SHARED`: relevant upstream state is visible, with at most one handoff;
- `L3_AGENTIC_FLEXIBLE`: shared state plus dynamic handoff choice, with up to three handoffs.

`L4_WHOLE_WORKFLOW_GATE_REPLAY` does not call an LLM. It evaluates the exact `L3` trajectory as a whole workflow against the Policy Box.

## Model cohorts

The design intentionally keeps two cohorts separate.

### OpenAI replication cohort

`GPT-5.6 Sol`, `GPT-5.6 Terra`, and `GPT-5.6 Luna` reproduce the earlier within-provider design. With 8 tasks, 4 generation conditions, and 10 repetitions per cell, this is exactly 960 trajectories.

### Cross-provider extension

`Claude Opus 5` and `Gemini 3.8 Flash` are added without changing the tasks, prompt contract, conditions, or evaluator. They add 640 trajectories. The total confirmatory schedule is 1,600.

The reason for keeping a named replication cohort is methodological rather than cosmetic. The prior result can be checked on the same 960-cell design. The extra providers then answer the narrower generalization question: does the mechanism appear when the generation model comes from a different provider?

Unless a provider contrast is frozen as a hypothesis before data collection, provider-level differences should be presented descriptively rather than promoted to a post-hoc confirmatory claim.

## Pilot and freeze rule

Before confirmatory collection, the code runs a 40-trajectory excluded engineering pilot: 5 models x 2 tasks x 4 generation conditions. The pilot checks compatibility and execution behavior. It is not part of the evidentiary sample.

After the pilot passes, `experiments/14_freeze_confirmatory.py` hashes the experiment-defining files. The ready state is committed and tagged `confirmatory-ready-v1.0`.

The live collector checks that exact tag, the clean working tree, the pilot validation, the randomized schedule, and the frozen manifest before it runs.

## Statistical plan

Event rates use Wilson 95% intervals for descriptive comparability.

The inherited confirmatory tests remain:

- H1: `L3` executed-bridge rate is higher than `L1`;
- H2: at least one `L3` bridge trajectory produces a policy-defined institutional decision;
- H3: every UCA classification preserves local authorization and owner-faithful scope;
- H4: every `L3` trajectory meeting the frozen governance-review criterion is routed to review in paired `L4` replay; and
- H5: bridge-opportunity tasks have a higher `L3` executed-bridge rate than negative-control/local-resolution tasks.

H1 and H5 use absolute risk differences and 10,000 cluster-bootstrap replicates at the model-by-task level. The analysis reports these tests for the full frozen five-model cohort and separately for the exact OpenAI replication subset.

The repository does not treat the laboratory event rate as a prevalence estimate for real organizations.
