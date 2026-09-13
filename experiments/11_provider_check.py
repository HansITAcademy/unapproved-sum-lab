from unapproved_sum.llm import run_trajectory
from unapproved_sum.policy_box import load_policy_box
from unapproved_sum.protocol import load_conditions, load_models, load_tasks
from unapproved_sum.providers import make_provider


def main() -> None:
    box = load_policy_box()
    task = next(t for t in load_tasks() if t.task_id == "T08_MONITOR_ONLY_SUPPLIER_CASE")
    condition = next(c for c in load_conditions() if c.condition_id == "L0_ISOLATED_LOCAL")
    for slot, spec in load_models().items():
        provider = make_provider(spec, max_attempts=2)
        result = run_trajectory(box, task, condition, provider)
        assert result.local_authorization_ok and result.owner_scope_ok
        print(f"PASS {slot:<14} {spec.provider:<10} {spec.model_id}")
    print("PROVIDER CHECK: PASS")
    print("These calls are engineering checks only and are not part of the evidentiary sample.")


if __name__ == "__main__":
    main()
