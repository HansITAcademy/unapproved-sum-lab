from unapproved_sum.protocol import (
    expected_trajectory_count,
    generation_conditions,
    load_models,
    load_tasks,
    openai_replication_count,
    validate_protocol,
)
from unapproved_sum.schedule import build_schedule


def test_protocol_validates_cleanly():
    assert validate_protocol() == ()


def test_eight_tasks_and_four_generation_conditions_are_frozen():
    assert len(load_tasks()) == 8
    assert len(generation_conditions()) == 4


def test_openai_replication_is_exactly_960_trajectories():
    assert openai_replication_count() == 960


def test_cross_provider_extension_is_1600_trajectories():
    assert expected_trajectory_count() == 1600


def test_model_registry_contains_original_three_openai_models():
    models = load_models()
    ids = [m.model_id for m in models.values() if m.cohort == "openai_replication"]
    assert ids == ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"]


def test_provider_set_has_openai_anthropic_and_gemini():
    assert {m.provider for m in load_models().values()} == {"openai", "anthropic", "gemini"}


def test_schedule_has_one_unique_row_per_planned_cell():
    rows = build_schedule()
    assert len(rows) == 1600
    cells = {(r.model_slot, r.task_id, r.condition_id, r.repetition) for r in rows}
    assert len(cells) == 1600
