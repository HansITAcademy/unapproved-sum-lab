# Unapproved Sum Lab

This is the clean computational lab for my **Unapproved Sum / Compiled Authority** research. I rebuilt it from the publication study so the experiment can be run from a fresh repository without carrying over old branches, draft folders, reading notes, or historical artifacts.

The question is simple even if the implementation is not: **can individually authorized agent actions compose into an institutional decision that the workflow itself was never authorized to make?**

The lab keeps three checks separate:

> local action authorization != workflow/process approval != institutional decision-right

That distinction matters throughout the code. A run is not classified as Unapproved Compiled Authority (UCA) just because an agent hands work to another agent. The connected path has to instantiate a policy-defined institutional decision, while the local actions remain authorized and the workflow lacks the decision-right or approval bundle required for that decision.

## What is in this repository

Only the lab. No literature-review folder, manuscript drafts, novelty matrix, slide deck, or old branch history.

The deterministic side reproduces the Policy Box and causal-composition tests. The probabilistic side uses the same eight business tasks and the same four generation conditions across model providers.

For the live confirmatory study I am keeping the original OpenAI experiment intact as a replication subset:

- GPT-5.6 Sol
- GPT-5.6 Terra
- GPT-5.6 Luna

That is still **3 models x 8 tasks x 4 generation conditions x 10 repetitions = 960 trajectories**.

I then add a cross-provider extension using:

- Claude Opus 5
- Gemini 3.8 Flash

With those two additions, the full run is **5 models x 8 tasks x 4 conditions x 10 repetitions = 1,600 trajectories**. The Claude/Gemini extension uses the exact same task files, condition files, prompt template, decision rules, and deterministic evaluator. Provider comparisons are descriptive unless they were frozen as an inferential test before collection.

`L4` is not another model generation. It replays each `L3` trajectory through the whole-workflow Authority Gate.

## Repository layout

```text
config/                 model registry and experiment settings
scenarios/              frozen tasks, conditions, prompts, and Policy Box
evidence/authority_corpus/
                        civilian decision-right grounding used by the lab
src/unapproved_sum/     experiment engine and provider adapters
experiments/            scripts to run in numerical order
tests/                  automated checks
results/                generated deterministic and redacted result artifacts
runtime/                raw pilot/confirmatory output (ignored by Git)
docs/                   short methods and run instructions
```

## Ground rules for this clean run

I am using **one branch: `main`**. I do not need a development branch, publication branch, or a trail of abandoned experimental branches for this run.

I use one Git tag, `confirmatory-ready-v1.0`, immediately before evidentiary collection. The tag is not a second branch. It is just a fixed pointer to the exact code and protocol state that produced the confirmatory data.

I also keep raw provider output out of Git. The collector writes it under `runtime/`. After collection, the redaction step produces a publication-safe result file under `results/`.

## Setup

I use Python 3.12+ and `uv`.

```bash
uv sync --dev
cp .env.example .env
```

Put the API keys in your shell or local `.env` file. Do **not** commit the `.env` file.

```text
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GEMINI_API_KEY=...
```

The code itself reads environment variables. If you use a `.env` file, load it into your shell before running the live steps.

## Run it in order

### 1. Start with tests

```bash
uv run pytest -q
uv run python experiments/08_validate_protocol.py
```

### 2. Reproduce the deterministic lab

```bash
uv run python experiments/01_authority_corpus.py
uv run python experiments/02_proof_of_mechanism.py
uv run python experiments/03_control_specificity.py
uv run python experiments/04_reproducibility_check.py
uv run python experiments/05_policy_box_emergence.py
uv run python experiments/06_bridge_subset_ablation.py
uv run python experiments/07_visibility_and_sod.py
```

These scripts do not call a model API.

### 3. Build the frozen randomized schedule and test the plumbing

```bash
uv run python experiments/09_generate_schedule.py
uv run python experiments/10_dry_run.py
```

The dry run uses a deterministic mock response. It has zero evidentiary weight.

### 4. Check that all five live model adapters actually work

```bash
uv run python experiments/11_provider_check.py
```

This makes a small number of live calls. It is an engineering check and is excluded from the study.

### 5. Run the excluded pilot

```bash
uv run python experiments/12_excluded_pilot.py --live
uv run python experiments/13_validate_pilot.py
```

The pilot is 40 trajectories: 5 models x 2 tasks x 4 conditions. It exists to catch API, schema, logging, replay, and failure-handling problems before the real collection. It is not included in the confirmatory statistics.

This is the last point where I allow myself to fix an implementation problem. If the pilot exposes a bug, I fix it, rerun the tests, regenerate the schedule if necessary, and rerun the pilot. I do not silently tune prompts because I dislike a behavioral result.

### 6. Freeze the exact confirmatory implementation

```bash
uv run python experiments/14_freeze_confirmatory.py
```

Then commit the entire ready state and tag it:

```bash
git add .
git commit -m "Freeze confirmatory protocol"
git tag confirmatory-ready-v1.0
git push origin main
git push origin confirmatory-ready-v1.0
```

Now run the strict preflight:

```bash
uv run python experiments/15_preflight.py --require-tag
```

The preflight refuses to proceed if the tree is dirty, the tag does not point to `HEAD`, the pilot validation is missing, the schedule or manifest changed, or one of the required API keys is missing.

### 7. Run the confirmatory collection

```bash
uv run python experiments/16_collect.py \
  --live \
  --confirm CONFIRM_EVIDENTIARY_COLLECTION
```

The collector is append-only. It prints technical progress but does not print bridge/UCA outcomes while collection is still running. A terminal run is never replaced. If the process is interrupted, use:

```bash
uv run python experiments/16_collect.py \
  --live \
  --resume \
  --confirm CONFIRM_EVIDENTIARY_COLLECTION
```

A trajectory that had started but did not get a terminal record is marked `interrupted_unknown`; it is not quietly regenerated.

### 8. Validate first, then redact, then analyze

```bash
uv run python experiments/17_validate_ledger.py
uv run python experiments/18_redact.py
uv run python experiments/19_analyze.py
```

The analysis produces the overall five-model confirmatory summary **and** a separate `openai_replication_subset` summary, so I can compare the new run directly with the original 960-trajectory design without muddying the replication with the cross-provider extension.

## Moving this into the new GitHub repository

If this folder was downloaded as a ZIP, I would initialize it like this:

```bash
git init
git branch -M main
git remote add origin https://github.com/HansITAcademy/unapproved-sum-lab.git
git add .
git commit -m "Clean lab rebuild"
git push -u origin main
```

After that, I stay on `main` for the entire study.

## A note on model settings

I keep the original OpenAI settings used in the earlier experiment: medium reasoning, temperature 1.0, no top-p override, and structured JSON output.

Claude and Gemini use the closest native equivalents: medium effort/thinking and schema-constrained JSON. Claude keeps temperature 1.0; Gemini 3.8 Flash does not get a temperature/top-p override because Google’s current migration guidance says to remove those sampling parameters and use `thinking_level` instead. Their output-token limits are larger because the providers account for reasoning/output budgets differently. I am matching the behavioral contract, not pretending the providers expose identical inference controls. The exact settings are frozen in `config/models.json` and described in `docs/provider_notes.md`.

## AI-assisted coding disclosure

I designed the research question, conceptual framework, experimental design, task structure, hypotheses, and interpretation. I used ChatGPT to accelerate parts of the software implementation and cleanup of this lab. I reviewed the code, ran the tests, and take responsibility for the implementation and the findings.

That disclosure is also kept in `docs/ai_assistance.md` so it does not get lost when the repository is shared independently from the paper.

## What I would not change after the ready tag

Once `confirmatory-ready-v1.0` exists, I would not alter tasks, prompts, model IDs, provider settings, repetitions, classification rules, hypotheses, or the evaluator and still call the result the same confirmatory study. A necessary post-freeze change should become a clearly labeled amendment or a new experiment.

That is the whole point of this rebuild: one clean repository, one visible protocol, one reproducible run path.
