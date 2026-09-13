from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .pilot import PILOT_VALIDATION_PATH
from .protocol import expected_trajectory_count, load_experiment
from .schedule import SCHEDULE_PATH


MANIFEST_PATH = Path("results/confirmatory_manifest.json")

# These are the files that define the experiment before the evidentiary run begins.
# If any of them changes after the manifest is written, preflight will fail.
CRITICAL_PATHS = (
    "config/experiment.json",
    "config/models.json",
    "scenarios/grounded_cases.json",
    "scenarios/policy_box.json",
    "scenarios/tasks.json",
    "scenarios/conditions.json",
    "scenarios/prompt_template.txt",
    "scenarios/repair_template.txt",
    "scenarios/randomization_schedule.json",
    "src/unapproved_sum/models.py",
    "src/unapproved_sum/authorization.py",
    "src/unapproved_sum/composition.py",
    "src/unapproved_sum/evaluation.py",
    "src/unapproved_sum/policy_box.py",
    "src/unapproved_sum/path_governance.py",
    "src/unapproved_sum/llm.py",
    "src/unapproved_sum/protocol.py",
    "src/unapproved_sum/providers.py",
    "src/unapproved_sum/schedule.py",
    "src/unapproved_sum/pilot.py",
    "src/unapproved_sum/confirmatory.py",
    "src/unapproved_sum/analysis.py",
    "experiments/16_collect.py",
    "experiments/17_validate_ledger.py",
    "experiments/18_redact.py",
    "experiments/19_analyze.py",
)


def sha256_path(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_manifest(path: Path | str = MANIFEST_PATH) -> dict[str, Any]:
    missing = [rel for rel in CRITICAL_PATHS if not Path(rel).exists()]
    if missing:
        raise FileNotFoundError("missing_critical_files:" + "|".join(missing))
    if not SCHEDULE_PATH.exists():
        raise FileNotFoundError(f"schedule_missing:{SCHEDULE_PATH}")
    if not PILOT_VALIDATION_PATH.exists():
        raise FileNotFoundError(f"pilot_validation_missing:{PILOT_VALIDATION_PATH}")
    pilot = json.loads(PILOT_VALIDATION_PATH.read_text(encoding="utf-8"))
    if pilot.get("validation_pass") is not True:
        raise RuntimeError("pilot_validation_must_pass_before_freeze")

    experiment = load_experiment()
    payload = {
        "artifact_version": "confirmatory-ready-v1.0",
        "status": "FROZEN_BEFORE_CONFIRMATORY_COLLECTION",
        "protocol_id": experiment["protocol_id"],
        "required_ready_tag": experiment["ready_tag"],
        "planned_trajectories": expected_trajectory_count(),
        "pilot_validation_sha256": sha256_path(PILOT_VALIDATION_PATH),
        "critical_input_sha256": {rel: sha256_path(rel) for rel in CRITICAL_PATHS},
    }
    path = Path(path)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def validate_manifest(path: Path | str = MANIFEST_PATH) -> tuple[str, ...]:
    p = Path(path)
    if not p.exists():
        return (f"manifest_missing:{p}",)
    payload = json.loads(p.read_text(encoding="utf-8"))
    errors: list[str] = []
    if payload.get("planned_trajectories") != expected_trajectory_count():
        errors.append("manifest_planned_trajectory_count_mismatch")
    if not PILOT_VALIDATION_PATH.exists():
        errors.append("pilot_validation_missing")
    elif payload.get("pilot_validation_sha256") != sha256_path(PILOT_VALIDATION_PATH):
        errors.append("pilot_validation_hash_mismatch")
    for rel, expected in payload.get("critical_input_sha256", {}).items():
        target = Path(rel)
        if not target.exists():
            errors.append(f"frozen_input_missing:{rel}")
        elif sha256_path(target) != expected:
            errors.append(f"frozen_input_hash_mismatch:{rel}")
    return tuple(errors)
