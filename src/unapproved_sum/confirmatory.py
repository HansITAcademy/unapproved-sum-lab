from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from .llm import (
    AgentCallRecord,
    TrajectoryResult,
    _append_target_workflow,
    _path_to_event,
    parse_agent_choice,
    render_prompt,
    whole_workflow_gate_replay,
)
from .manifest import MANIFEST_PATH, sha256_path, validate_manifest
from .path_governance import evaluate_policy_box
from .pilot import PILOT_VALIDATION_PATH, replay_to_dict
from .policy_box import load_policy_box
from .protocol import (
    MODELS_PATH,
    REPAIR_TEMPLATE_PATH,
    expected_trajectory_count,
    load_conditions,
    load_experiment,
    load_models,
    load_tasks,
)
from .providers import make_provider, sha256_text
from .schedule import SCHEDULE_PATH, validate_schedule


RAW_LEDGER_PATH = Path("runtime/confirmatory_raw.jsonl")
TERMINAL_STATUSES = frozenset({"completed", "failed", "interrupted_unknown"})
CONFIRMATION_PHRASE = "CONFIRM_EVIDENTIARY_COLLECTION"


@dataclass(frozen=True)
class LedgerState:
    metadata: dict[str, Any] | None
    latest_by_run_id: dict[str, dict[str, Any]]
    events_by_run_id: dict[str, tuple[dict[str, Any], ...]]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    return completed.stdout.strip()


def current_git_state() -> dict[str, str]:
    return {
        "branch": _git("branch", "--show-current"),
        "head": _git("rev-parse", "HEAD"),
        "status": _git("status", "--porcelain"),
    }


def tag_commit(tag: str) -> str:
    return _git("rev-list", "-n", "1", tag)


def load_schedule() -> list[dict[str, Any]]:
    payload = json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))
    return list(payload["rows"])


def _required_api_keys() -> dict[str, str]:
    providers = {spec.provider for spec in load_models().values()}
    mapping = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }
    return {provider: mapping[provider] for provider in providers}


def validate_pilot_gate() -> tuple[str, ...]:
    if not PILOT_VALIDATION_PATH.exists():
        return ("pilot_validation_missing",)
    payload = json.loads(PILOT_VALIDATION_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    if payload.get("validation_pass") is not True:
        errors.append("pilot_validation_not_passed")
    if payload.get("failed") != 0:
        errors.append(f"pilot_failures:{payload.get('failed')}")
    return tuple(errors)


def validate_live_readiness(*, require_tag: bool = True) -> tuple[str, ...]:
    errors: list[str] = []
    state = current_git_state()
    if state["branch"] != "main":
        errors.append(f"expected_main_branch:{state['branch']}")
    if state["status"]:
        errors.append("working_tree_not_clean")

    experiment = load_experiment()
    ready_tag = experiment["ready_tag"]
    if require_tag:
        try:
            expected_head = tag_commit(ready_tag)
        except Exception:
            errors.append(f"required_tag_missing:{ready_tag}")
        else:
            if state["head"] != expected_head:
                errors.append(f"head_not_at_ready_tag:{state['head']}:{expected_head}")
        for provider, env_name in _required_api_keys().items():
            if not os.getenv(env_name):
                errors.append(f"api_key_missing:{provider}:{env_name}")

    errors.extend(validate_pilot_gate())
    errors.extend(validate_schedule())
    errors.extend(validate_manifest())
    schedule = load_schedule() if SCHEDULE_PATH.exists() else []
    if len(schedule) != expected_trajectory_count():
        errors.append(f"schedule_count:{len(schedule)}:{expected_trajectory_count()}")
    return tuple(errors)


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def read_ledger(path: Path | str = RAW_LEDGER_PATH) -> LedgerState:
    p = Path(path)
    if not p.exists():
        return LedgerState(metadata=None, latest_by_run_id={}, events_by_run_id={})
    metadata: dict[str, Any] | None = None
    latest: dict[str, dict[str, Any]] = {}
    histories: dict[str, list[dict[str, Any]]] = {}
    for line_no, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"ledger_invalid_json_line:{line_no}") from exc
        if record.get("record_type") == "metadata":
            if metadata is not None:
                raise ValueError("ledger_multiple_metadata_records")
            metadata = record
            continue
        if record.get("record_type") != "run_state":
            raise ValueError(f"ledger_unknown_record_type:{line_no}")
        run_id = record.get("run_id")
        if not isinstance(run_id, str):
            raise ValueError(f"ledger_missing_run_id:{line_no}")
        histories.setdefault(run_id, []).append(record)
        latest[run_id] = record
    return LedgerState(
        metadata=metadata,
        latest_by_run_id=latest,
        events_by_run_id={key: tuple(value) for key, value in histories.items()},
    )


def _metadata_record() -> dict[str, Any]:
    experiment = load_experiment()
    return {
        "record_type": "metadata",
        "collection_id": "UCA-CROSS-PROVIDER-001",
        "protocol_id": experiment["protocol_id"],
        "evidentiary": True,
        "created_utc": utc_now(),
        "planned_trajectories": expected_trajectory_count(),
        "schedule_sha256": sha256_path(SCHEDULE_PATH),
        "model_registry_sha256": sha256_path(MODELS_PATH),
        "policy_box_sha256": sha256_path("scenarios/policy_box.json"),
        "manifest_sha256": sha256_path(MANIFEST_PATH),
        "confirmatory_ready_tag": experiment["ready_tag"],
        "confirmatory_ready_commit": tag_commit(experiment["ready_tag"]),
    }


def _validate_existing_metadata(metadata: dict[str, Any]) -> tuple[str, ...]:
    expected = _metadata_record()
    errors: list[str] = []
    for key in (
        "collection_id", "protocol_id", "evidentiary", "planned_trajectories",
        "schedule_sha256", "model_registry_sha256", "policy_box_sha256",
        "manifest_sha256", "confirmatory_ready_tag", "confirmatory_ready_commit",
    ):
        if metadata.get(key) != expected.get(key):
            errors.append(f"ledger_metadata_mismatch:{key}")
    return tuple(errors)


def _trajectory_to_raw_dict(result: TrajectoryResult, repair_events: list[dict[str, Any]]) -> dict[str, Any]:
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
                "prompt": call.prompt,
                "prompt_sha256": sha256_text(call.prompt),
                "raw_response": call.raw_response,
                "response_sha256": sha256_text(call.raw_response),
                "parsed_choice": asdict(call.parsed_choice),
            }
            for call in result.calls
        ],
        "repair_events": repair_events,
    }


def _repair_prompt(original_prompt: str, raw_response: str, parser_error: str) -> str:
    template = REPAIR_TEMPLATE_PATH.read_text(encoding="utf-8")
    return template.format(
        prompt_sha256=sha256_text(original_prompt),
        parser_error=parser_error,
        raw_response=raw_response,
    )


def run_trajectory_with_repair(policy_box: Any, task: Any, condition: Any, provider: Any) -> tuple[TrajectoryResult, list[dict[str, Any]]]:
    if not condition.generation_condition:
        raise ValueError("replay_condition_cannot_generate")
    event_path = _path_to_event(policy_box, task.start_event_id)
    current_event_id = task.start_event_id
    proposed: list[tuple[str, str]] = []
    executed: list[tuple[str, str]] = []
    calls: list[AgentCallRecord] = []
    repair_events: list[dict[str, Any]] = []

    for step_index in range(condition.max_cross_workflow_handoffs + 1):
        prompt, offered = render_prompt(policy_box, task, condition, current_event_id, event_path)
        raw = provider.generate(
            prompt, task_id=task.task_id, condition_id=condition.condition_id,
            step_index=step_index, current_event_id=current_event_id,
        )
        try:
            choice = parse_agent_choice(raw, frozenset(offered))
        except ValueError as exc:
            parser_error = str(exc)
            if parser_error == "handoff_target_not_offered":
                raise ValueError("substantive_invalid_target_no_repair") from exc
            repair_prompt = _repair_prompt(prompt, raw, parser_error)
            repaired_raw = provider.generate(
                repair_prompt, task_id=task.task_id, condition_id=condition.condition_id,
                step_index=step_index, current_event_id=current_event_id,
            )
            repair_events.append(
                {
                    "step_index": step_index,
                    "current_event_id": current_event_id,
                    "parser_error": parser_error,
                    "original_response_sha256": sha256_text(raw),
                    "repair_prompt_sha256": sha256_text(repair_prompt),
                    "repaired_response_sha256": sha256_text(repaired_raw),
                }
            )
            choice = parse_agent_choice(repaired_raw, frozenset(offered))
            raw = repaired_raw

        calls.append(
            AgentCallRecord(
                step_index=step_index, current_event_id=current_event_id,
                prompt=prompt, raw_response=raw, parsed_choice=choice,
            )
        )
        if choice.action == "stop":
            break
        edge = offered[choice.target_agent_id]
        proposed.append(edge)
        if len(executed) >= condition.max_cross_workflow_handoffs:
            break
        executed.append(edge)
        current_event_id = _append_target_workflow(policy_box, edge[1], event_path)
        if len(executed) >= condition.max_cross_workflow_handoffs:
            break

    evaluation = evaluate_policy_box(
        policy_box, condition=condition.condition_id, active_bridges=frozenset(executed)
    )
    return TrajectoryResult(
        task_id=task.task_id,
        condition_id=condition.condition_id,
        event_path=tuple(event_path),
        proposed_bridges=tuple(proposed),
        executed_bridges=tuple(executed),
        calls=tuple(calls),
        compiled_decisions=evaluation.compiled_decisions,
        unauthorized_decisions=evaluation.unauthorized_decisions,
        unapproved_process_decisions=evaluation.unapproved_process_decisions,
        sod_failures=evaluation.sod_failures,
        emergent_paths=evaluation.emergent_paths,
        local_authorization_ok=evaluation.local_authorization_ok,
        owner_scope_ok=evaluation.owner_scope_ok,
        uca=evaluation.uca,
    ), repair_events


def _terminalize_interrupted(path: Path, state: LedgerState) -> int:
    count = 0
    for run_id, latest in sorted(state.latest_by_run_id.items()):
        if latest.get("status") == "started":
            _append_jsonl(
                path,
                {
                    "record_type": "run_state",
                    "run_id": run_id,
                    "sequence": latest.get("sequence"),
                    "model_slot": latest.get("model_slot"),
                    "task_id": latest.get("task_id"),
                    "condition_id": latest.get("condition_id"),
                    "repetition": latest.get("repetition"),
                    "status": "interrupted_unknown",
                    "timestamp_utc": utc_now(),
                    "exclusion_reason": "process_interrupted_after_started_before_terminal_record",
                },
            )
            count += 1
    return count


def collect_confirmatory(*, path: Path | str = RAW_LEDGER_PATH, resume: bool = False) -> Path:
    readiness = validate_live_readiness(require_tag=True)
    if readiness:
        raise RuntimeError("confirmatory_readiness_failed:" + "|".join(readiness))

    path = Path(path)
    state = read_ledger(path)
    if path.exists() and not resume:
        raise RuntimeError("confirmatory_ledger_exists_use_resume")
    if resume and not path.exists():
        raise RuntimeError("resume_requested_but_ledger_missing")

    if state.metadata is None:
        _append_jsonl(path, _metadata_record())
    else:
        metadata_errors = _validate_existing_metadata(state.metadata)
        if metadata_errors:
            raise RuntimeError("confirmatory_ledger_metadata_failed:" + "|".join(metadata_errors))

    if resume:
        state = read_ledger(path)
        interrupted = _terminalize_interrupted(path, state)
        if interrupted:
            print(f"Marked interrupted-unknown without rerun: {interrupted}")

    state = read_ledger(path)
    schedule = load_schedule()
    tasks = {task.task_id: task for task in load_tasks()}
    conditions = {condition.condition_id: condition for condition in load_conditions()}
    specs = load_models()
    box = load_policy_box()

    already_terminal = {
        run_id for run_id, record in state.latest_by_run_id.items()
        if record.get("status") in TERMINAL_STATUSES
    }
    if any(record.get("status") == "started" for record in state.latest_by_run_id.values()):
        raise RuntimeError("nonterminal_started_record_requires_resume")

    for row in schedule:
        run_id = row["run_id"]
        if run_id in already_terminal:
            continue
        slot = row["model_slot"]
        spec = specs[slot]
        _append_jsonl(
            path,
            {"record_type": "run_state", **row, "status": "started", "timestamp_utc": utc_now()},
        )
        print(
            f"START {run_id} {slot} {row['task_id']} {row['condition_id']} rep={row['repetition']}",
            flush=True,
        )

        provider = make_provider(spec, max_attempts=3)
        try:
            result, repair_events = run_trajectory_with_repair(
                box, tasks[row["task_id"]], conditions[row["condition_id"]], provider
            )
            replay = None
            if row["condition_id"] == "L3_AGENTIC_FLEXIBLE":
                replay = replay_to_dict(whole_workflow_gate_replay(box, result))
            terminal = {
                "record_type": "run_state",
                **row,
                "status": "completed",
                "timestamp_utc": utc_now(),
                "provider": spec.provider,
                "model_id": spec.model_id,
                "cohort": spec.cohort,
                "trajectory": _trajectory_to_raw_dict(result, repair_events),
                "l4_replay": replay,
                "provider_audit": provider.audit_dicts(),
                "provider_errors": provider.error_log,
            }
            _append_jsonl(path, terminal)
            print(f"DONE  {run_id} completed", flush=True)
        except Exception as exc:
            terminal = {
                "record_type": "run_state",
                **row,
                "status": "failed",
                "timestamp_utc": utc_now(),
                "provider": spec.provider,
                "model_id": spec.model_id,
                "cohort": spec.cohort,
                "error_type": type(exc).__name__,
                "error": str(exc)[:2000],
                "provider_audit": provider.audit_dicts(),
                "provider_errors": provider.error_log,
                "exclusion_reason": "terminal_technical_failure",
            }
            _append_jsonl(path, terminal)
            print(f"DONE  {run_id} failed", flush=True)
    return path


def validate_raw_ledger(path: Path | str = RAW_LEDGER_PATH) -> tuple[str, ...]:
    state = read_ledger(path)
    errors: list[str] = []
    if state.metadata is None:
        return ("ledger_missing_metadata",)
    errors.extend(_validate_existing_metadata(state.metadata))
    schedule = load_schedule()
    schedule_by_id = {row["run_id"]: row for row in schedule}
    if set(state.latest_by_run_id) != set(schedule_by_id):
        missing = set(schedule_by_id).difference(state.latest_by_run_id)
        extra = set(state.latest_by_run_id).difference(schedule_by_id)
        if missing:
            errors.append(f"ledger_missing_run_ids:{len(missing)}")
        if extra:
            errors.append(f"ledger_extra_run_ids:{len(extra)}")

    for run_id, expected in schedule_by_id.items():
        latest = state.latest_by_run_id.get(run_id)
        if latest is None:
            continue
        if latest.get("status") not in TERMINAL_STATUSES:
            errors.append(f"ledger_nonterminal:{run_id}:{latest.get('status')}")
        for key in ("sequence", "model_slot", "task_id", "condition_id", "repetition"):
            if latest.get(key) != expected.get(key):
                errors.append(f"ledger_schedule_mismatch:{run_id}:{key}")
        history = state.events_by_run_id.get(run_id, ())
        starts = [item for item in history if item.get("status") == "started"]
        terminals = [item for item in history if item.get("status") in TERMINAL_STATUSES]
        if len(starts) != 1:
            errors.append(f"ledger_start_count:{run_id}:{len(starts)}")
        if len(terminals) != 1:
            errors.append(f"ledger_terminal_count:{run_id}:{len(terminals)}")
        if latest.get("status") == "completed":
            trajectory = latest.get("trajectory", {})
            if trajectory.get("local_authorization_ok") is not True:
                errors.append(f"design_invariant_local_authorization:{run_id}")
            if trajectory.get("owner_scope_ok") is not True:
                errors.append(f"design_invariant_owner_scope:{run_id}")
            if expected["condition_id"] == "L3_AGENTIC_FLEXIBLE" and latest.get("l4_replay") is None:
                errors.append(f"missing_l4_replay:{run_id}")
            if expected["condition_id"] != "L3_AGENTIC_FLEXIBLE" and latest.get("l4_replay") is not None:
                errors.append(f"unexpected_l4_replay:{run_id}")
    return tuple(errors)
