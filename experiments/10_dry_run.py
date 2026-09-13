from unapproved_sum.llm import MockProvider, run_trajectory, whole_workflow_gate_replay
from unapproved_sum.policy_box import load_policy_box
from unapproved_sum.protocol import generation_conditions, load_tasks


def main() -> None:
    box = load_policy_box()
    runs = 0
    replays = 0
    for task in load_tasks():
        for condition in generation_conditions():
            # The mock deliberately stops. This is a plumbing test, not a behavioral result.
            provider = MockProvider(box)
            result = run_trajectory(box, task, condition, provider)
            assert result.local_authorization_ok
            assert result.owner_scope_ok
            runs += 1
            if condition.condition_id == "L3_AGENTIC_FLEXIBLE":
                replay = whole_workflow_gate_replay(box, result)
                assert replay.source_condition_id == "L3_AGENTIC_FLEXIBLE"
                replays += 1
    print("DRY RUN: PASS")
    print("Mock trajectories:", runs)
    print("L4 replays:", replays)


if __name__ == "__main__":
    main()
