# Provider notes

Last checked for this rebuild: **13 September 2026**.

The live model registry is in `config/models.json`. That file, not this prose note, is the machine-readable source of truth for a run.

## Why I did not force fake parameter equality

The providers expose different inference APIs. I therefore hold the experimental *behavioral contract* constant:

- same business task;
- same visible state for a given condition;
- same handoff limits;
- same prompt template;
- same JSON response schema;
- same temperature target of 1.0 where the current provider API supports/encourages it;
- medium native reasoning/effort setting;
- same Python semantic parser; and
- same deterministic Policy Box evaluator.

I do not claim that `medium` reasoning on OpenAI, `medium` effort on Anthropic, and `medium` thinking on Gemini are computationally identical.

## OpenAI

Models:

- `gpt-5.6-sol`
- `gpt-5.6-terra`
- `gpt-5.6-luna`

Adapter: Responses API with strict JSON Schema output. The original replication settings are retained: medium reasoning effort, temperature 1.0, no top-p override, 512 maximum output tokens, and `store=false`.

Reference: OpenAI model/API documentation at `platform.openai.com/docs`.

## Anthropic

Model: `claude-opus-5`.

Adapter: Messages API using `output_config` with medium effort and JSON Schema structured output. The output budget is 4096 tokens.

Reference: Anthropic model and structured-output documentation at `docs.anthropic.com` / `platform.claude.com/docs`.

## Gemini

Model: `gemini-3.8-flash`.

Adapter: Google Gen AI Interactions API with medium thinking and JSON Schema response formatting. I intentionally do not send `temperature`, `top_p`, or `top_k` for Gemini 3.8 Flash because Google’s current migration guidance says to remove those sampling parameters. The output budget is 4096 tokens.

Reference: Gemini API documentation at `ai.google.dev/gemini-api/docs`.

## Why only one Claude and one Gemini in the confirmatory extension

The original OpenAI cohort is already a three-variant within-family comparison. For the first clean cross-provider extension I use one current model from Anthropic and one from Google rather than adding a large, uneven collection of preview and older-tier models.

That keeps the main question readable and the run count manageable: 960 exact-replication trajectories plus 640 cross-provider trajectories. If I later want Opus/Sonnet/Haiku or several Gemini tiers, I would run that as a separately frozen extension rather than changing this confirmatory schedule after seeing its results.

## Provider check before the pilot

`experiments/11_provider_check.py` makes a small excluded live call to every configured model. This is the first place to catch a retired model ID or SDK/API change. If a provider changes an API before confirmatory collection begins, I update the adapter, rerun all tests and the excluded pilot, and freeze the final code only after it passes.

After the ready tag is created, a model substitution is an amendment, not a silent implementation detail.
