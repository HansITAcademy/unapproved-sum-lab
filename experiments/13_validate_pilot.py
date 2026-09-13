import json

from unapproved_sum.pilot import PILOT_PATH, PILOT_VALIDATION_PATH, build_pilot_cells, validate_pilot_payload


def main() -> None:
    if not PILOT_PATH.exists():
        raise SystemExit(f"Pilot file missing: {PILOT_PATH}")
    payload = json.loads(PILOT_PATH.read_text(encoding="utf-8"))
    errors = validate_pilot_payload(payload)
    validation = {
        "pilot_id": payload.get("pilot_id"),
        "evidentiary": False,
        "planned": len(build_pilot_cells()),
        "completed": payload.get("trajectory_count_completed"),
        "failed": payload.get("trajectory_count_failed"),
        "l4_replays": len(payload.get("l4_replays", [])),
        "validation_pass": not errors,
        "validation_errors": list(errors),
    }
    PILOT_VALIDATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    PILOT_VALIDATION_PATH.write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(validation, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
