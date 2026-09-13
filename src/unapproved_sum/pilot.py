from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .llm import run_trajectory, whole_workflow_gate_replay
from .policy_box import load_policy_box
from .protocol import load_conditions, load_experiment, load_models, load_tasks
from .providers import make_provider


PILOT_PATH = Path("runtime/excluded_pilot.json")
PILOT_VALIDATION_PATH = Path("results/pilot_validation.json")


@dataclass(frozen=True)
class PilotCell:
    sequence: int
    run_id: str
    model_slot: str
    task_id: str
    condition_id: str


def build_pilot_cells() -> tuple[PilotCell, ...]:
    experiment = load_experiment()
    task_ids = tuple(experiment["pilot_task_ids"])
    condition_ids = tuple(experiment["pilot_condition_ids"])
    model_slots = tuple(load_models())
    cells: list[PilotCell] = []
    n = 0
    for model_slot in model_slots:
        for task_id in task_ids:
            for condition_id in condition_ids:
                n += 1
                cells.append(
                    PilotCell(
                        sequence=n,
                        run_id=f"PILOT-{n:03d}",
                        model_slot=model_slot,
                        task_id=task_id,
                        condition_id=condition_id,
                    )
                )
    return tuple(cells)


def trajectory_to_dict(result: Any, *, include_prompts: bool = False) -> dict[str, Any]:
    return {
        "task_id": result.task_id,
        "condition_id": result.condition_id,
        "event_path": list(result.event_path),
        "proposed_bridges": [list(edge) for edge in result.proposed_bridges],
        "executed_bridges": [list(edge) for edge in result.executed_bridges],
        "compiled_decisions": list(result.compiled_decisions),
        "unauthorized_decisions": list(result.unauthorized_decisions),
        "unapproved_process_decisions": list(result.unapproved_process_decisions),
        "sod_failures": list(result.sod_failures),
        "emergent_paths": [list(path) for path in result.emergent_paths],
        "local_authorization_ok": result.local_authorization_ok,
        "owner_scope_ok": result.owner_scope_ok,
        "uca": result.uca,
        "calls": [
            {
                "step_index": call.step_index,
                "current_event_id": call.current_event_id,
                **({"prompt": call.prompt} if include_prompts else {}),
                "raw_response": call.raw_response,
                "parsed_choice": asdict(call.parsed_choice),
            }
            for call in result.calls
        ],
    }


def replay_to_dict(replay: Any) -> dict[str, Any]:
    return {
        "task_id": replay.task_id,
        "source_condition_id": replay.source_condition_id,
        "proposed_bridges": [list(edge) for edge in replay.proposed_bridges],
        "process_review_required": replay.process_review_required,
        "authority_review_required": replay.authority_review_required,
        "sod_review_required": replay.sod_review_required,
        "whole_workflow_review_required": replay.whole_workflow_review_required,
        "execute_without_review": replay.execute_without_review,
        "compiled_decisions": list(replay.compiled_decisions),
        "unauthorized_decisions": list(replay.unauthorized_decisions),
        "sod_failures": list(replay.sod_failures),
    }


def run_excluded_pilot(path: Path | str = PILOT_PATH) -> Path:
    box = load_policy_box()
    tasks = {task.task_id: task for task in load_tasks()}
    conditions = {condition.condition_id: condition for condition in load_conditions()}
    specs = load_models()

    rows: list[dict[str, Any]] = []
    l3_results: dict[tuple[str, str], Any] = {}
    audit: dict[str, list[dict[str, Any]]] = {slot: [] for slot in specs}
    errors_by_slot: dict[str, list[dict[str, Any]]] = {slot: [] for slot in specs}

    for cell in build_pilot_cells():
        spec = specs[cell.model_slot]
        provider = make_provider(spec, max_attempts=3)
        row: dict[str, Any] = {
            **asdict(cell),
            "evidentiary": False,
            "status": "pending",
            "provider": spec.provider,
            "model_id": spec.model_id,
        }
        try:
            result = run_trajectory(box, tasks[cell.task_id], conditions[cell.condition_id], provider)
            row["status"] = "completed"
            row["trajectory"] = trajectory_to_dict(result)
            if cell.condition_id == "L3_AGENTIC_FLEXIBLE":
                l3_results[(cell.model_slot, cell.task_id)] = result
        except Exception as exc:
            row["status"] = "failed"
            row["error_type"] = type(exc).__name__
            row["error"] = str(exc)[:2000]
        audit[cell.model_slot].extend(provider.audit_dicts())
        errors_by_slot[cell.model_slot].extend(provider.error_log)
        rows.append(row)

    l4_replays: list[dict[str, Any]] = []
    for (model_slot, task_id), result in sorted(l3_results.items()):
        spec = specs[model_slot]
        l4_replays.append(
            {
                "model_slot": model_slot,
                "provider": spec.provider,
                "model_id": spec.model_id,
                "task_id": task_id,
                "evidentiary": False,
                "replay": replay_to_dict(whole_workflow_gate_replay(box, result)),
            }
        )

    cells = build_pilot_cells()
    payload = {
        "protocol_id": load_experiment()["protocol_id"],
        "pilot_id": "UCA-EXCLUDED-PILOT-001",
        "evidentiary": False,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "trajectory_count_planned": len(cells),
        "trajectory_count_completed": sum(row["status"] == "completed" for row in rows),
        "trajectory_count_failed": sum(row["status"] == "failed" for row in rows),
        "rows": rows,
        "l4_replays": l4_replays,
        "provider_audit": audit,
        "provider_errors": errors_by_slot,
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def validate_pilot_payload(payload: dict[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    expected_cells = build_pilot_cells()
    rows = payload.get("rows", [])
    if payload.get("evidentiary") is not False:
        errors.append("pilot_must_be_non_evidentiary")
    if len(rows) != len(expected_cells):
        errors.append(f"pilot_row_count:{len(rows)}:{len(expected_cells)}")
    observed = {(r.get("model_slot"), r.get("task_id"), r.get("condition_id")) for r in rows}
    expected = {(c.model_slot, c.task_id, c.condition_id) for c in expected_cells}
    if observed != expected:
        errors.append("pilot_cell_set_mismatch")
    failures = [row for row in rows if row.get("status") != "completed"]
    if failures:
        errors.append(f"pilot_failures:{len(failures)}")
    experiment = load_experiment()
    expected_replays = len(load_models()) * len(experiment["pilot_task_ids"])
    if len(payload.get("l4_replays", [])) != expected_replays:
        errors.append(f"pilot_l4_replay_count:{len(payload.get('l4_replays', []))}:{expected_replays}")
    for row in rows:
        if row.get("status") == "completed":
            trajectory = row.get("trajectory", {})
            if trajectory.get("local_authorization_ok") is not True:
                errors.append(f"pilot_local_authorization_failed:{row.get('run_id')}")
            if trajectory.get("owner_scope_ok") is not True:
                errors.append(f"pilot_owner_scope_failed:{row.get('run_id')}")
    return tuple(errors)
