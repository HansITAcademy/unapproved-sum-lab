# Follow-up Study: Independent Recipient Decisions

This is a **new draft study**. Its outputs must not be pooled with, or used to
retroactively repair, the frozen 1,600-trajectory study. The original files and
confirmatory manifest remain unchanged.

## Why a branch

Use the existing `Agent-to-choose-own-actions` branch in the canonical GitHub
repository. The supplied ZIP had no `.git` history, so install this extension
in your GitHub Codespace, which does preserve repository ancestry. In the
Codespace terminal:

```bash
git switch Agent-to-choose-own-actions
git branch --show-current
```

Install only the new follow-up files listed below. Commit them on this branch,
leaving `confirmatory-ready-v1.0`, all files hashed by its manifest, and the
original results untouched. The follow-up must receive a **new** protocol ID,
schedule, freeze tag, raw ledger, redacted data, and analysis script before any
confirmatory run.

## What the draft extension does now

`followup.py` asks the existing route agent whether to request another function.
The recipient then **independently chooses** whether to execute its own first
local action; each further local agent chooses whether to perform its own
action. Declined actions are absent from the resulting path. The evaluator
uses **the actually executed event path** instead of assuming that a recipient
completed its entire workflow. It can enforce a pre-action authority/process
gate or observe an ungated path.

The new task context records whether the two $50,000 commitments are in the
same program. T05 is related; T06 is unrelated. The threshold is computed by
group, so the T06 false authority flags cannot be reproduced by merely using
the generic `related_commitment_total` event field.

Four synthetic controls separate process approval and decision authority:
`missing_both`, `process_only`, `authority_only`, and `approved_both`. In the
authorized control, the same decision can occur without UCA if its required
decision grant and distinct approval actors are present. The control **does
not** establish that any real enterprise has made those delegations.

New files:

- `src/unapproved_sum/followup.py`
- `src/unapproved_sum/followup_openai.py`
- `scenarios/followup_study.json`
- `experiments/20_followup_dry_run.py`
- `experiments/21_followup_live_pilot.py`
- `tests/test_followup.py`
- `docs/followup_branch_guide.md`

## Verify without model calls

From the canonical project root after copying the new files:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_followup.py' -v
PYTHONPATH=src python experiments/20_followup_dry_run.py
```

The dry run is scripted plumbing only. The tests show an independent recipient
can decline; a locally chosen second approval can cross the related-program
threshold; T06 stays unrelated; and an authorized decision is distinct from an
approved process.

## Optional excluded live engineering pilot

With the project's SDK dependencies installed and `OPENAI_API_KEY` set:

```bash
PYTHONPATH=src python experiments/21_followup_live_pilot.py \
  --task T05_RELATED_COMMITMENT_THRESHOLD \
  --control missing_both \
  --model gpt-5.6-sol \
  --confirm EXCLUDED_PILOT_ONLY
```

The pilot writes raw role prompts and model replies under
`runtime/followup_pilot_raw.jsonl`, which the existing `.gitignore` excludes.
It is **not** a new confirmatory result. The adapter is OpenAI-only for the
engineering pilot; the core harness accepts any provider implementing
`choose`, and a multi-provider study needs adapters tested and frozen before
collection. Each role receives its own stateless prompt; separate role calls
do not establish that the organization's actual agents would behave likewise.

## Before a publishable follow-up collection

1. Get two qualified domain reviewers to approve or revise the four synthetic
   decision rules, including what counts as a supplier suspension and when
   commitments are related. Preserve their individual blinded responses.
2. Decide the primary outcome **before collection**: for example, the fraction
   of model-requested handoffs whose recipients execute the consequential
   action, and the fraction of actually executed paths that meet a validated
   decision rule without the required approval. Predefine a positive authorized
   control and a negative unrelated-commitment control.
3. Specify a contemporaneous scripted-recipient comparator with an identical
   initial request. Do not compare new model rates causally with the archived
   1,600 trajectories, whose provider versions or prompts may differ. Freeze
   the comparator and the endpoint together.
4. Specify model slots, sample size per task/control, randomization, failures,
   stopping, and uncertainty analysis. Run and exclude an engineering pilot.
5. Freeze new inputs and collection code with a new manifest and Git tag such
   as `followup-ready-v1.0`. Verify an external timestamp or release record.
   Collect to a new append-only raw ledger; keep errors, hashes, and redacted
   publication data separate from the original study.

The present code implements the path-accurate multi-agent mechanism and pilot,
but **steps 1–5 are outstanding**. Do not present its scripted dry-run as live
evidence or claim a confirmatory follow-up has been run.
