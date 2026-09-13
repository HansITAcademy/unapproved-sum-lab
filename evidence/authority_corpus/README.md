# Civilian Institutional Decision-Right Corpus

This directory contains the external authority evidence used to ground the publication model.

## Files

- `decision_rights.csv` — coded decision-right records.
- `sources.json` — official primary-source metadata.
- `coding_protocol.md` — coding rules and construct definitions.

## Scope

The current corpus contains **45 records from 18 official civilian sources** spanning procurement, human resources, professional responsibility, enforcement, regulatory policy, benefits adjudication, internal policy governance, and federal payment operations.

No Department of Defense or military sources are included.

## What the corpus establishes

The corpus documents that real civilian institutions use multiple authority structures, including:

- bounded delegation;
- reserved final authority;
- proposal versus final-decision separation;
- monetary and categorical thresholds;
- nonredelegable grants;
- multiple required approvals;
- sequential multi-role authority chains; and
- review/override authority.

This supports the publication model's core assumption that **local grants do not automatically aggregate into workflow-level decision authority**.

## What the corpus does not establish

It does not estimate how common UCA is.
It does not show that any named institution currently has an agentic UCA problem.
It does not prove that every documented policy can be represented by one universal hierarchy.

Run:

```bash
uv run python experiments/00_analyze_authority_corpus.py
```
