from collections import Counter

from unapproved_sum.authority_corpus import (
    EXCLUDED_DEFENSE_TERMS,
    load_records,
    load_sources,
    summarize_corpus,
    validate_corpus,
)


def test_corpus_has_no_validation_errors():
    assert validate_corpus(load_records(), load_sources()) == []


def test_corpus_has_publication_scale_and_source_diversity():
    summary = summarize_corpus(load_records(), load_sources())
    assert summary["records"] >= 40
    assert summary["sources"] >= 15
    assert summary["organizations"] >= 8
    assert summary["domains"] >= 8


def test_all_sources_are_official_government_primary_sources():
    sources = load_sources()
    assert all(source.official_primary_source for source in sources.values())
    assert all(".gov" in source.url for source in sources.values())


def test_defense_and_military_material_is_excluded():
    records = load_records()
    sources = load_sources()
    text = " ".join(
        [
            *(
                " ".join(
                    (
                        record.organization,
                        record.domain,
                        record.decision,
                        record.local_actor,
                        record.required_authority,
                    )
                )
                for record in records
            ),
            *(
                " ".join((source.publisher, source.title, source.url))
                for source in sources.values()
            ),
        ]
    ).lower()
    assert not any(term in text for term in EXCLUDED_DEFENSE_TERMS)


def test_core_policy_relative_patterns_are_present():
    patterns = {record.authority_pattern for record in load_records()}
    required = {
        "bounded_delegation",
        "reserved_role",
        "threshold_escalation",
        "proposal_decision_split",
        "nonredelegable_grant",
        "joint_approval",
        "multi_role_chain",
    }
    assert required.issubset(patterns)


def test_proposal_final_split_is_supported_across_multiple_organizations():
    orgs = {
        record.organization
        for record in load_records()
        if record.authority_pattern == "proposal_decision_split"
    }
    assert len(orgs) >= 4


def test_threshold_escalation_is_supported_across_multiple_organizations():
    orgs = {
        record.organization
        for record in load_records()
        if record.authority_pattern == "threshold_escalation"
    }
    assert len(orgs) >= 3


def test_multiple_authority_or_multi_role_requirements_exist():
    records = load_records()
    patterns = Counter(record.authority_pattern for record in records)
    assert patterns["joint_approval"] >= 1
    assert patterns["multi_role_chain"] >= 2


def test_corpus_is_not_dominated_by_one_source_or_organization():
    summary = summarize_corpus(load_records(), load_sources())
    assert summary["max_source_share"] <= 0.25
    assert summary["max_organization_share"] <= 0.30


def test_every_record_has_traceable_source_locator_and_support_summary():
    for record in load_records():
        assert record.source_locator.strip()
        assert len(record.support_summary.strip()) >= 30
        assert record.verification_status == "verified_primary"
