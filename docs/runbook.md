# Runbook

This is the short version I can keep open while running the lab.

## Before any live call

```bash
uv sync --dev
uv run pytest -q
uv run python experiments/08_validate_protocol.py
```

Run `01` through `07`, then:

```bash
uv run python experiments/09_generate_schedule.py
uv run python experiments/10_dry_run.py
```

Set `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `GEMINI_API_KEY` in the environment.

## Excluded engineering calls

```bash
uv run python experiments/11_provider_check.py
uv run python experiments/12_excluded_pilot.py --live
uv run python experiments/13_validate_pilot.py
```

If the pilot fails because of code/API compatibility, fix the implementation now and repeat the checks. Do not use the pilot to tune the study toward a preferred substantive outcome.

## Freeze

```bash
uv run python experiments/14_freeze_confirmatory.py
git add .
git commit -m "Freeze confirmatory protocol"
git tag confirmatory-ready-v1.0
git push origin main
git push origin confirmatory-ready-v1.0
uv run python experiments/15_preflight.py --require-tag
```

Do not edit the frozen experiment after this point.

## Collect

```bash
uv run python experiments/16_collect.py --live --confirm CONFIRM_EVIDENTIARY_COLLECTION
```

Resume only if needed:

```bash
uv run python experiments/16_collect.py --live --resume --confirm CONFIRM_EVIDENTIARY_COLLECTION
```

Do not manually delete failed or interrupted cells to make the sample look complete.

## After the collector is terminal

```bash
uv run python experiments/17_validate_ledger.py
uv run python experiments/18_redact.py
uv run python experiments/19_analyze.py
```

Keep `runtime/confirmatory_raw.jsonl` private/local unless there is a specific reason to preserve it in a controlled research archive. The redacted artifact under `results/` is the version meant for the public repository.
