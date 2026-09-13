import json

import pytest

from unapproved_sum.confirmatory import run_trajectory_with_repair
from unapproved_sum.llm import MockProvider, parse_agent_choice, run_trajectory, whole_workflow_gate_replay
from unapproved_sum.policy_box import load_policy_box
from unapproved_sum.protocol import load_conditions, load_tasks


def _choice(action="stop", target=None):
    return json.dumps({
        "action": action,
        "target_agent_id": target,
        "rationale": "Frozen test choice.",
        "confidence": 0.8,
    })


class SequenceProvider:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def generate(self, prompt, *, task_id, condition_id, step_index, current_event_id):
        self.calls.append((task_id, condition_id, step_index, current_event_id))
        if not self.outputs:
            raise RuntimeError("no_more_outputs")
        return self.outputs.pop(0)


def _task(task_id):
    return next(t for t in load_tasks() if t.task_id == task_id)


def _condition(condition_id):
    return next(c for c in load_conditions() if c.condition_id == condition_id)


def test_parser_accepts_minimal_valid_stop():
    choice = parse_agent_choice(_choice(), frozenset())
    assert choice.action == "stop"
    assert choice.target_agent_id is None


def test_parser_rejects_unoffered_target():
    with pytest.raises(ValueError, match="handoff_target_not_offered"):
        parse_agent_choice(_choice("handoff", "NOT_OFFERED"), frozenset({"agent_x"}))


def test_isolated_condition_cannot_execute_bridge():
    box = load_policy_box()
    result = run_trajectory(box, _task("T01_SUPPLIER_RISK_PAYMENT_HOLD"), _condition("L0_ISOLATED_LOCAL"), MockProvider(box))
    assert result.executed_bridges == ()


def test_whole_workflow_gate_replays_exact_l3_bridge_set():
    box = load_policy_box()
    task = _task("T08_MONITOR_ONLY_SUPPLIER_CASE")
    condition = _condition("L3_AGENTIC_FLEXIBLE")
    result = run_trajectory(box, task, condition, MockProvider(box))
    replay = whole_workflow_gate_replay(box, result)
    assert replay.proposed_bridges == result.proposed_bridges
    assert replay.source_condition_id == "L3_AGENTIC_FLEXIBLE"


def test_confirmatory_path_matches_base_path_without_repair():
    box = load_policy_box()
    task = _task("T08_MONITOR_ONLY_SUPPLIER_CASE")
    condition = _condition("L1_CONNECTED_OPAQUE")
    original = run_trajectory(box, task, condition, SequenceProvider([_choice()]))
    confirmatory, repairs = run_trajectory_with_repair(box, task, condition, SequenceProvider([_choice()]))
    assert confirmatory.event_path == original.event_path
    assert confirmatory.executed_bridges == original.executed_bridges
    assert confirmatory.compiled_decisions == original.compiled_decisions
    assert confirmatory.uca == original.uca
    assert repairs == []


def test_confirmatory_allows_one_schema_repair():
    box = load_policy_box()
    provider = SequenceProvider(["not-json", _choice()])
    result, repairs = run_trajectory_with_repair(
        box,
        _task("T08_MONITOR_ONLY_SUPPLIER_CASE"),
        _condition("L1_CONNECTED_OPAQUE"),
        provider,
    )
    assert result.executed_bridges == ()
    assert len(repairs) == 1
    assert len(provider.calls) == 2


def test_invalid_unoffered_target_is_not_repaired():
    box = load_policy_box()
    provider = SequenceProvider([_choice("handoff", "NOT_AN_OFFERED_AGENT"), _choice()])
    with pytest.raises(ValueError, match="substantive_invalid_target_no_repair"):
        run_trajectory_with_repair(
            box,
            _task("T08_MONITOR_ONLY_SUPPLIER_CASE"),
            _condition("L1_CONNECTED_OPAQUE"),
            provider,
        )
    assert len(provider.calls) == 1
