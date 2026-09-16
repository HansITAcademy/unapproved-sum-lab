"""Offline demonstration only; no model output and no evidentiary results."""
from __future__ import annotations

import json
from pathlib import Path

from unapproved_sum.followup import FollowupContext, ScriptedFollowupAgent, grant_from_config, run_followup, to_json
from unapproved_sum.policy_box import load_policy_box
from unapproved_sum.protocol import load_tasks


def main() -> None:
    config = json.loads(Path("scenarios/followup_study.json").read_text())
    box = load_policy_box()
    tasks = {task.task_id: task for task in load_tasks()}
    task = tasks["T05_RELATED_COMMITMENT_THRESHOLD"]
    context = FollowupContext(config["commitment_groups"][task.task_id])
    script = ScriptedFollowupAgent({
        ("agent_commit_1_approve", "route"): "handoff:L",
        ("agent_commit_2_prepare", "local"): "execute",
        ("agent_commit_2_approve", "local"): "execute",
    })
    for control in ("missing_both", "process_only", "authority_only", "approved_both"):
        result = run_followup(box, task, script, context, grant_from_config(config, control))
        print(control, to_json(result))
    print("DRY RUN ONLY: scripted choices are not evidence; no original result was modified.")


if __name__ == "__main__":
    main()
