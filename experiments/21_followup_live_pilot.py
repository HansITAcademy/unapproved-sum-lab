"""One excluded live engineering pilot; never combined with original or follow-up results."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from unapproved_sum.followup import FollowupContext, grant_from_config, run_followup
from unapproved_sum.followup_openai import OpenAIFollowupAgent
from unapproved_sum.policy_box import load_policy_box
from unapproved_sum.protocol import load_tasks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", default="T05_RELATED_COMMITMENT_THRESHOLD")
    parser.add_argument("--control", default="missing_both")
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    if args.confirm != "EXCLUDED_PILOT_ONLY":
        parser.error("Pilot requires --confirm EXCLUDED_PILOT_ONLY")
    config_path = Path("scenarios/followup_study.json")
    config = json.loads(config_path.read_text())
    tasks = {t.task_id: t for t in load_tasks()}
    agent = OpenAIFollowupAgent(args.model)
    result = run_followup(
        load_policy_box(), tasks[args.task], agent,
        FollowupContext(config["commitment_groups"].get(args.task, {})),
        grant_from_config(config, args.control),
    )
    record = {
        "study": config["protocol_id"], "status": "excluded_engineering_pilot",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "model_id": args.model, "control": args.control,
        "result": asdict(result), "model_calls": agent.calls,
    }
    path = Path("runtime/followup_pilot_raw.jsonl")
    path.parent.mkdir(exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")
    print(f"Excluded pilot recorded in {path}; {len(agent.calls)} role choices. "
          "Not evidence and not part of the original study.")


if __name__ == "__main__":
    main()
