from unapproved_sum.analysis import wilson_interval
from unapproved_sum.pilot import build_pilot_cells, validate_pilot_payload


def test_excluded_pilot_has_40_cells_for_five_models():
    cells = build_pilot_cells()
    assert len(cells) == 40
    assert len({(c.model_slot, c.task_id, c.condition_id) for c in cells}) == 40


def test_pilot_validator_rejects_missing_cells():
    errors = validate_pilot_payload({"evidentiary": False, "rows": [], "l4_replays": []})
    assert any(error.startswith("pilot_row_count") for error in errors)
    assert "pilot_cell_set_mismatch" in errors


def test_wilson_interval_handles_empty_and_nonempty_samples():
    assert wilson_interval(0, 0) == (None, None)
    low, high = wilson_interval(5, 10)
    assert low is not None and high is not None
    assert 0 < low < 0.5 < high < 1
