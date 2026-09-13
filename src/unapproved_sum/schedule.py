from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import random

from .protocol import generation_conditions, load_experiment, load_models, load_tasks


SCHEDULE_PATH = Path("scenarios/randomization_schedule.json")


@dataclass(frozen=True)
class ScheduleRow:
    sequence: int
    run_id: str
    model_slot: str
    task_id: str
    condition_id: str
    repetition: int


def build_schedule() -> tuple[ScheduleRow, ...]:
    experiment = load_experiment()
    seed = int(experiment["schedule_seed"])
    repetitions = int(experiment["repetitions_per_cell"])
    model_slots = tuple(load_models())
    tasks = load_tasks()
    conditions = generation_conditions()

    cells: list[tuple[str, str, str, int]] = []
    for model_slot in model_slots:
        for task in tasks:
            for condition in conditions:
                for repetition in range(1, repetitions + 1):
                    cells.append((model_slot, task.task_id, condition.condition_id, repetition))

    rng = random.Random(seed)
    rng.shuffle(cells)
    return tuple(
        ScheduleRow(
            sequence=index,
            run_id=f"UCA-{index:05d}",
            model_slot=model_slot,
            task_id=task_id,
            condition_id=condition_id,
            repetition=repetition,
        )
        for index, (model_slot, task_id, condition_id, repetition) in enumerate(cells, start=1)
    )


def write_schedule(path: Path | str = SCHEDULE_PATH) -> Path:
    path = Path(path)
    rows = build_schedule()
    experiment = load_experiment()
    payload = {
        "protocol_id": experiment["protocol_id"],
        "seed": int(experiment["schedule_seed"]),
        "repetitions_per_cell": int(experiment["repetitions_per_cell"]),
        "model_slots": list(load_models()),
        "total_generation_trajectories": len(rows),
        "rows": [asdict(row) for row in rows],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def validate_schedule(path: Path | str = SCHEDULE_PATH) -> tuple[str, ...]:
    path = Path(path)
    if not path.exists():
        return (f"schedule_missing:{path}",)
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("rows", [])
    experiment = load_experiment()
    expected_rows = build_schedule()
    expected = [asdict(row) for row in expected_rows]
    errors: list[str] = []

    if rows != expected:
        errors.append("schedule_does_not_match_frozen_inputs")
    run_ids = [row.get("run_id") for row in rows]
    if len(run_ids) != len(set(run_ids)):
        errors.append("duplicate_run_id")
    if [row.get("sequence") for row in rows] != list(range(1, len(rows) + 1)):
        errors.append("sequence_not_contiguous")
    if payload.get("seed") != int(experiment["schedule_seed"]):
        errors.append("schedule_seed_mismatch")
    if tuple(payload.get("model_slots", [])) != tuple(load_models()):
        errors.append("model_slots_mismatch")
    return tuple(errors)
