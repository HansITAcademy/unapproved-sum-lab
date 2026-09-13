from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ALLOWED_PATTERNS = frozenset(
    {
        "bounded_delegation",
        "approval_prerequisite",
        "reserved_role",
        "threshold_escalation",
        "proposal_decision_split",
        "nonredelegable_grant",
        "joint_approval",
        "multi_role_chain",
        "review_override",
    }
)

ALLOWED_REDELEGATION = frozenset(
    {"allowed", "not_allowed", "conditional", "not_stated"}
)

ALLOWED_FINALITY = frozenset(
    {"local", "intermediate", "final", "review", "mixed"}
)

EXCLUDED_DEFENSE_TERMS = (
    "department of defense",
    "defense department",
    "dod",
    "dfars",
    "army",
    "navy",
    "air force",
    "marine corps",
    "space force",
    "military",
)


@dataclass(frozen=True)
class AuthorityRecord:
    record_id: str
    source_id: str
    organization: str
    domain: str
    decision: str
    local_actor: str
    local_right: str
    required_authority: str
    authority_pattern: str
    threshold_or_condition: str
    redelegation: str
    finality: str
    source_locator: str
    support_summary: str
    verification_status: str


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    publisher: str
    title: str
    url: str
    source_date_or_version: str
    accessed: str
    official_primary_source: bool


def default_corpus_dir() -> Path:
    return Path("evidence/authority_corpus")


def load_records(path: Path | None = None) -> list[AuthorityRecord]:
    path = path or default_corpus_dir() / "decision_rights.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        return [AuthorityRecord(**row) for row in csv.DictReader(handle)]


def load_sources(path: Path | None = None) -> dict[str, SourceRecord]:
    path = path or default_corpus_dir() / "sources.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        item["source_id"]: SourceRecord(**item)
        for item in raw
    }


def validate_corpus(
    records: Iterable[AuthorityRecord],
    sources: dict[str, SourceRecord],
) -> list[str]:
    records = list(records)
    errors: list[str] = []

    if not records:
        errors.append("corpus_has_no_records")
        return errors

    record_ids = [record.record_id for record in records]
    duplicates = sorted(
        record_id
        for record_id, count in Counter(record_ids).items()
        if count > 1
    )
    if duplicates:
        errors.append("duplicate_record_ids:" + ",".join(duplicates))

    for record in records:
        if record.source_id not in sources:
            errors.append(f"{record.record_id}:unknown_source:{record.source_id}")
            continue

        if record.authority_pattern not in ALLOWED_PATTERNS:
            errors.append(
                f"{record.record_id}:invalid_pattern:{record.authority_pattern}"
            )

        if record.redelegation not in ALLOWED_REDELEGATION:
            errors.append(
                f"{record.record_id}:invalid_redelegation:{record.redelegation}"
            )

        if record.finality not in ALLOWED_FINALITY:
            errors.append(
                f"{record.record_id}:invalid_finality:{record.finality}"
            )

        required_fields = (
            record.organization,
            record.domain,
            record.decision,
            record.local_actor,
            record.local_right,
            record.required_authority,
            record.source_locator,
            record.support_summary,
            record.verification_status,
        )
        if any(not value.strip() for value in required_fields):
            errors.append(f"{record.record_id}:blank_required_field")

        source = sources[record.source_id]
        combined = " ".join(
            (
                record.organization,
                record.domain,
                record.decision,
                record.local_actor,
                record.local_right,
                record.required_authority,
                source.publisher,
                source.title,
                source.url,
            )
        ).lower()

        for excluded in EXCLUDED_DEFENSE_TERMS:
            if excluded in combined:
                errors.append(f"{record.record_id}:excluded_defense_term:{excluded}")

    for source_id, source in sources.items():
        if not source.official_primary_source:
            errors.append(f"{source_id}:not_marked_official_primary")
        if ".gov" not in source.url:
            errors.append(f"{source_id}:non_gov_source:{source.url}")

    used_sources = {record.source_id for record in records}
    unused_sources = sorted(set(sources) - used_sources)
    if unused_sources:
        errors.append("unused_sources:" + ",".join(unused_sources))

    return errors


def summarize_corpus(
    records: Iterable[AuthorityRecord],
    sources: dict[str, SourceRecord],
) -> dict:
    records = list(records)

    by_pattern = Counter(record.authority_pattern for record in records)
    by_domain = Counter(record.domain for record in records)
    by_organization = Counter(record.organization for record in records)
    by_source = Counter(record.source_id for record in records)

    max_org_share = max(by_organization.values()) / len(records)
    max_source_share = max(by_source.values()) / len(records)

    return {
        "records": len(records),
        "sources": len(sources),
        "organizations": len(by_organization),
        "domains": len(by_domain),
        "patterns": dict(sorted(by_pattern.items())),
        "records_by_domain": dict(sorted(by_domain.items())),
        "records_by_organization": dict(sorted(by_organization.items())),
        "records_by_source": dict(sorted(by_source.items())),
        "max_organization_share": round(max_org_share, 4),
        "max_source_share": round(max_source_share, 4),
        "joint_or_multi_role_records": sum(
            by_pattern[pattern]
            for pattern in ("joint_approval", "multi_role_chain")
        ),
        "proposal_decision_split_records": by_pattern["proposal_decision_split"],
        "threshold_escalation_records": by_pattern["threshold_escalation"],
        "reserved_role_records": by_pattern["reserved_role"],
        "nonredelegable_records": by_pattern["nonredelegable_grant"],
    }
