Unapproved Sum Lab

Publication package date: 23 September 2026

This repository contains the clean computational lab for The Unapproved Sum / Compiled Authority research. It was rebuilt from the publication study so the experiment can be reproduced from a fresh repository without carrying forward draft branches, reading notes, slide decks, or historical working files.

The central question is:

Can individually authorized agent actions compose into an institutional decision that the workflow itself was never authorized to make?

The lab keeps three governance objects separate:

local action authorization != workflow/process approval != institutional decision-right

That distinction is the core of the study. A run is not classified as Unapproved Compiled Authority (UCA) merely because one agent hands work to another. UCA requires all of the following: the constituent actions remain locally authorized; the agents remain within the operative scope of their human or organizational owners; the connected causal path instantiates a policy-defined institutional decision; and the workflow lacks the decision-right or approval bundle required for that decision.

Publication snapshot

The deterministic study tests the Policy Box, whole-workflow Authority Gate, process-approval controls, decision-right controls, bridge-subset ablations, and separation-of-duties cases.

The confirmatory study uses five model slots across three providers:

GPT-5.6 Sol

GPT-5.6 Terra

GPT-5.6 Luna

Claude Opus 5

Gemini 3.8 Flash

The three OpenAI models form the 960-trajectory replication subset:

3 models x 8 tasks x 4 generation conditions x 10 repetitions = 960 trajectories

Claude and Gemini add a 640-trajectory cross-provider extension:

2 models x 8 tasks x 4 generation conditions x 10 repetitions = 640 trajectories

The full frozen confirmatory schedule is therefore:

5 models x 8 tasks x 4 generation conditions x 10 repetitions = 1,600 scheduled trajectories

Of those 1,600 scheduled trajectories, 1,584 completed. Sixteen Claude Opus 5 T05 trajectories were preserved as terminal technical failures rather than replaced.

Key publication results are preserved under results/:

L0 completed: 400; executed bridges: 0; UCA: 0

L1 completed: 399; executed bridges: 207 (51.9%); UCA: 157

L2 completed: 393; executed bridges: 208 (52.9%); UCA: 158

L3 completed: 392; executed bridges: 206 (52.6%); UCA: 156

Connected total, L1-L3: 621 executed bridges and 471 UCA classifications

All 471/471 UCA classifications preserve the study's local-authorization and owner-scope conditions

T03 bridges in 150/150 connected completed trajectories and produces 0 UCA events, demonstrating that cross-agent coordination is not itself classified as an authority violation

H1 is retained as a negative result: the L3-minus-L1 executed-bridge difference is approximately +0.67 percentage points and does not support the pre-specified prediction that added flexibility increases bridge formation

H5 is supported: L3 opportunity tasks bridge in 189/192 completed trajectories (98.4%) versus 17/200 (8.5%) for negative-controls tasks

The extreme-case missing-data sensitivity analysis leaves the H5 difference strongly positive

L4 is a deterministic paired replay rather than a new model generation; all 156/156 L3 trajectories meeting the pre-specified review criterion are routed to review

Nine live multi-hop trajectories appear in L3, all from Gemini 3.8 Flash

No live separation-of-duties failure appears in the confirmatory sample; that mechanism remains demonstrated in the deterministic controls

These rates are experimental results from the frozen task set. They are not prevalence estimates for real organizations.

Repository layout

config/                 model registry and experiment settings
scenarios/              frozen tasks, conditions, prompts, and Policy Box
evidence/authority_corpus/
                        civilian decision-right grounding used by the lab
src/unapproved_sum/     experiment engine and provider adapters
experiments/            scripts to run in numerical order
tests/                  automated checks
results/                deterministic and publication-safe result artifacts
runtime/                raw pilot/confirmatory output (ignored by Git)
docs/                   methods, provider notes, disclosure, and run instructions

The repository contains the lab, not the manuscript's literature-review working folder, novelty matrix, slide deck, or abandoned draft branches.

Frozen protocol and provenance

The pre-collection protocol is identified by the Git tag:

confirmatory-ready-v1.0

results/confirmatory_manifest.json is the authoritative machine-readable record that the confirmatory protocol was frozen before evidentiary collection. It records the planned 1,600 trajectories and SHA-256 hashes for the critical configuration, scenario, source, and collection/analysis files.

Important frozen-file note

config/models.json contains the historical field:

"status": "DRAFT_UNTIL_PILOT_PASSES"

That label is a stale administrative string inside a frozen, hashed pre-collection input. It is intentionally left unchanged after collection because editing the file would destroy byte-for-byte correspondence with the recorded confirmatory manifest. The authoritative study status is the manifest field:

FROZEN_BEFORE_CONFIRMATORY_COLLECTION

The same principle applies to other frozen inputs: do not silently “clean up” a hashed confirmatory file after observing results. Post-collection clarifications belong in documentation, not in the evidence-generating inputs.

ZIP distributions and Git history

A downloaded ZIP preserves the repository files but does not preserve the .git directory or independently prove when a Git tag was created. The original Git repository, release record, or another immutable timestamped archive should therefore be retained as provenance for confirmatory-ready-v1.0.

The raw append-only runtime ledger is intentionally excluded from the public repository. The publication-safe dataset and summary artifacts preserve outcome variables and cryptographic linkage. For journal archiving, the raw ledger should be retained in restricted immutable storage together with external timestamp evidence for the frozen protocol state.

Setup

The project uses Python 3.12+ and uv.

uv sync --dev
cp .env.example .env

Provide API keys through the environment or a local .env file. Do not commit .env.

OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GEMINI_API_KEY=...

The code reads environment variables. If a .env file is used, load it into the shell before running live steps.

Reproduce the study

1. Run the automated checks

uv run pytest -q
uv run python experiments/08_validate_protocol.py

The pre-collection code state used by the study passed 65 automated tests.

2. Reproduce the deterministic lab

uv run python experiments/01_authority_corpus.py
uv run python experiments/02_proof_of_mechanism.py
uv run python experiments/03_control_specificity.py
uv run python experiments/04_reproducibility_check.py
uv run python experiments/05_policy_box_emergence.py
uv run python experiments/06_bridge_subset_ablation.py
uv run python experiments/07_visibility_and_sod.py

These scripts do not call a model API.

3. Build the randomized schedule and test the plumbing

uv run python experiments/09_generate_schedule.py
uv run python experiments/10_dry_run.py

The dry run uses deterministic mock output and has no evidentiary weight.

4. Check all live provider adapters

uv run python experiments/11_provider_check.py

This is an excluded engineering check used to catch model-ID, SDK, API, schema, or authentication problems before the pilot.

5. Run the excluded pilot

uv run python experiments/12_excluded_pilot.py --live
uv run python experiments/13_validate_pilot.py

The pilot contains 40 trajectories:

5 models x 2 tasks x 4 conditions = 40 excluded trajectories

Its purpose is to test API compatibility, structured output, logging, replay, and failure handling. Pilot results are not included in the confirmatory statistics.

The pilot is the final point at which an implementation problem may be fixed before the evidentiary run. Any fix requires rerunning the relevant tests and validation. Behavioral prompts are not tuned merely because a pilot result is inconvenient.

6. Freeze the confirmatory implementation

uv run python experiments/14_freeze_confirmatory.py

Then commit and tag the exact ready state:

git add .
git commit -m "Freeze confirmatory protocol"
git tag confirmatory-ready-v1.0
git push origin main
git push origin confirmatory-ready-v1.0

Run the strict preflight:

uv run python experiments/15_preflight.py --require-tag

The preflight is designed to reject a dirty tree, an incorrect tag/HEAD relationship, a missing pilot validation, changed schedule/manifest inputs, or missing provider credentials.

7. Run confirmatory collection

uv run python experiments/16_collect.py \
  --live \
  --confirm CONFIRM_EVIDENTIARY_COLLECTION

Collection is append-only. Successful and terminal trajectories are never replaced. If collection is interrupted:

uv run python experiments/16_collect.py \
  --live \
  --resume \
  --confirm CONFIRM_EVIDENTIARY_COLLECTION

A trajectory that started but did not receive a terminal ledger record is marked interrupted_unknown rather than silently regenerated.

8. Validate, redact, and analyze

uv run python experiments/17_validate_ledger.py
uv run python experiments/18_redact.py
uv run python experiments/19_analyze.py

The analysis produces the full five-model confirmatory summary and a separate openai_replication_subset summary. This keeps the 960-trajectory within-family replication analytically distinguishable from the 640-trajectory cross-provider extension.

Confirmatory conditions

The live experiment contains four generation conditions and one deterministic paired replay:

L0 — Isolated Local: no external agents are available

L1 — Connected Opaque: another function is reachable, with limited shared state and at most one handoff

L2 — Connected Shared: relevant shared state is visible, with at most one handoff

L3 — Agentic Flexible: shared state plus dynamic agent/tool choice, with up to three sequential handoffs

L4 — Whole-Workflow Gate Replay: no new model call; the exact L3 trajectory is replayed through the Policy Box/Authority Gate

L4 is therefore a governance evaluation of L3, not a fifth stochastic model condition.

Provider-setting clarification

The study holds the behavioral contract constant across providers: the same business task, condition-specific visible state, handoff constraints, response schema, semantic parser, and deterministic Policy Box evaluation. It does not claim that provider-native “medium” reasoning/thinking settings are computationally identical.

OpenAI

The OpenAI replication uses the configured GPT-5.6 Sol, Terra, and Luna slots through the Responses API with the frozen settings recorded in config/models.json.

Anthropic

The frozen config/models.json contains a historical temperature: 1.0 field under the Anthropic settings. The actual AnthropicProvider adapter does not transmit temperature, top_p, or top_k. The adapter uses the provider-native output_config for medium effort and structured JSON output. This is intentional and is documented in the source code and docs/provider_notes.md.

Do not edit the frozen configuration merely to make its prose-like fields match current provider terminology after the fact. The manifest hash preserves what was frozen; the adapter source preserves what was actually sent.

Gemini

Gemini 3.8 Flash uses medium thinking and schema-constrained response formatting. The adapter does not send temperature/top-p/top-k overrides under the frozen implementation.

Provider-specific output-token limits differ because the APIs account for reasoning and output budgets differently. The study matches the experimental contract rather than asserting parameter equality across providers.

Data handling and research integrity

The collector records each scheduled trajectory before and after execution. Completed runs and terminal technical failures are not replaced. Publication-safe output removes raw prompts, model rationales, and provider response identifiers while retaining the variables required to reproduce the reported analysis.

The confirmatory package includes, among other artifacts:

results/confirmatory_manifest.json
results/confirmatory_redacted.json
results/confirmatory_summary.json
results/confirmatory_rates.csv
results/confirmatory_block_table.csv
results/confirmatory_hypotheses.json
results/provider_summary.csv
results/missing_data_sensitivity.json

The raw runtime ledger remains outside the public ZIP/Git distribution. Reanalysis of the publication-safe outcome variables does not require new API calls. A new live run is a replication, not a replacement for the frozen confirmatory sample.

Authority corpus and semantic-policy limitation

The external authority corpus contains 45 coded decision-right records from 18 civilian primary sources across 11 coded institutional source groupings and 11 domains. It is a grounding set, not a representative sample and not evidence that UCA occurred in the institutions represented by those sources.

The Policy Box's semantic decision rules are researcher-specified for the synthetic experimental scenarios. That is an explicit limitation. Before journal submission, a stronger validation step would use at least two independent reviewers or domain experts, blinded to trajectory outcomes, to code the authority corpus and/or semantic decision classifications and report inter-rater agreement. A field study should additionally validate decision rules with actual process owners.

AI-assisted software-development disclosure

The research question, conceptual framework, experimental design, task structure, hypotheses, research methods, analysis, interpretation, and manuscript were developed by the author. OpenAI ChatGPT was used to accelerate portions of software coding, debugging, and implementation based on author-defined specifications.

The author reviewed the code and outputs, ran the automated and deterministic checks, and takes responsibility for the implementation and findings.

The same disclosure is preserved in docs/ai_assistance.md so it remains attached to the computational artifact when the repository is shared separately from the paper.

Moving a ZIP into a GitHub repository

If this folder is downloaded as a ZIP and is being initialized as a new repository:

git init
git branch -M main
git remote add origin https://github.com/HansITAcademy/unapproved-sum-lab.git
git add .
git commit -m "Clean lab rebuild"
git push -u origin main

For the actual confirmatory record, preserve the repository/release that contains the original frozen tag rather than treating a newly initialized ZIP as equivalent provenance.

Interpretation boundary

This lab is designed to test a specific mechanism:

locally authorized actions can form a connected causal workflow that instantiates a policy-defined institutional decision requiring authority not delegated to that workflow.

It does not claim that every cross-agent bridge is problematic, that the observed rates estimate enterprise prevalence, that every decision-right can be reduced to a scalar authority level, or that the whole-workflow gate solves policy interpretation automatically.

The intended governance implication is narrower: authorization of the components should not automatically be treated as authorization of the institutional decision produced by their composition.
