from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from .policy_box import load_policy_box


TASKS_PATH = Path("scenarios/tasks.json")
CONDITIONS_PATH = Path("scenarios/conditions.json")
PROMPT_TEMPLATE_PATH = Path("scenarios/prompt_template.txt")
REPAIR_TEMPLATE_PATH = Path("scenarios/repair_template.txt")
MODELS_PATH = Path("config/models.json")
EXPERIMENT_PATH = Path("config/experiment.json")


@dataclass(frozen=True)
class Task:
    task_id: str
    start_event_id: str
    task_text: str
    analysis_stratum: str
    expected_relevant_bridge_ids: tuple[str, ...]


@dataclass(frozen=True)
class Condition:
    condition_id: str
    description: str
    external_agents_visible: bool
    shared_state_visible: bool
    max_cross_workflow_handoffs: int
    generation_condition: bool
    paired_replay_of: str | None = None


@dataclass(frozen=True)
class ModelSpec:
    slot: str
    provider: str
    model_id: str
    snapshot: str
    display_name: str
    cohort: str
    settings: dict[str, Any]


def read_json(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_experiment() -> dict[str, Any]:
    return read_json(EXPERIMENT_PATH)


def load_tasks() -> tuple[Task, ...]:
    payload = read_json(TASKS_PATH)
    return tuple(
        Task(
            task_id=item["task_id"],
            start_event_id=item["start_event_id"],
            task_text=item["task_text"],
            analysis_stratum=item["analysis_stratum"],
            expected_relevant_bridge_ids=tuple(item.get("expected_relevant_bridge_ids", [])),
        )
        for item in payload["tasks"]
    )


def load_conditions() -> tuple[Condition, ...]:
    payload = read_json(CONDITIONS_PATH)
    return tuple(
        Condition(
            condition_id=item["condition_id"],
            description=item["description"],
            external_agents_visible=bool(item["external_agents_visible"]),
            shared_state_visible=bool(item["shared_state_visible"]),
            max_cross_workflow_handoffs=int(item["max_cross_workflow_handoffs"]),
            generation_condition=bool(item["generation_condition"]),
            paired_replay_of=item.get("paired_replay_of"),
        )
        for item in payload["conditions"]
    )


def load_models() -> dict[str, ModelSpec]:
    payload = read_json(MODELS_PATH)
    provider_settings = payload["provider_settings"]
    specs: dict[str, ModelSpec] = {}
    for item in payload["models"]:
        provider = item["provider"]
        if provider not in provider_settings:
            raise ValueError(f"missing_provider_settings:{provider}")
        spec = ModelSpec(
            slot=item["slot"],
            provider=provider,
            model_id=item["model_id"],
            snapshot=item["snapshot"],
            display_name=item["display_name"],
            cohort=item["cohort"],
            settings=dict(provider_settings[provider]),
        )
        if spec.slot in specs:
            raise ValueError(f"duplicate_model_slot:{spec.slot}")
        specs[spec.slot] = spec
    return specs


def generation_conditions() -> tuple[Condition, ...]:
    return tuple(c for c in load_conditions() if c.generation_condition)


def sha256_file(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def expected_trajectory_count() -> int:
    experiment = load_experiment()
    return (
        len(load_models())
        * len(load_tasks())
        * len(generation_conditions())
        * int(experiment["repetitions_per_cell"])
    )


def openai_replication_count() -> int:
    experiment = load_experiment()
    models = [m for m in load_models().values() if m.cohort == "openai_replication"]
    return (
        len(models)
        * len(load_tasks())
        * len(generation_conditions())
        * int(experiment["repetitions_per_cell"])
    )


def validate_protocol() -> tuple[str, ...]:
    errors: list[str] = []
    box = load_policy_box()
    tasks = load_tasks()
    conditions = load_conditions()
    models = load_models()
    experiment = load_experiment()

    if len(tasks) != 8:
        errors.append(f"expected_8_tasks:{len(tasks)}")
    if len({task.task_id for task in tasks}) != len(tasks):
        errors.append("duplicate_task_id")
    if len({c.condition_id for c in conditions}) != len(conditions):
        errors.append("duplicate_condition_id")
    if len(models) < 5:
        errors.append(f"expected_at_least_5_models:{len(models)}")

    providers = {spec.provider for spec in models.values()}
    if providers != {"openai", "anthropic", "gemini"}:
        errors.append(f"provider_set_mismatch:{sorted(providers)}")
    openai_models = [spec for spec in models.values() if spec.cohort == "openai_replication"]
    if len(openai_models) != 3:
        errors.append(f"openai_replication_model_count:{len(openai_models)}")

    known_events = set(box.events_by_id)
    known_bridge_ids = {b.bridge_id for b in box.bridge_candidates}
    for task in tasks:
        if task.start_event_id not in known_events:
            errors.append(f"unknown_task_start:{task.task_id}:{task.start_event_id}")
        unknown = set(task.expected_relevant_bridge_ids).difference(known_bridge_ids)
        if unknown:
            errors.append(f"unknown_expected_bridge:{task.task_id}:{sorted(unknown)}")

    by_id = {c.condition_id: c for c in conditions}
    expected_ids = {
        "L0_ISOLATED_LOCAL",
        "L1_CONNECTED_OPAQUE",
        "L2_CONNECTED_SHARED",
        "L3_AGENTIC_FLEXIBLE",
        "L4_WHOLE_WORKFLOW_GATE_REPLAY",
    }
    if set(by_id) != expected_ids:
        errors.append("condition_set_mismatch")
    if by_id.get("L0_ISOLATED_LOCAL") and by_id["L0_ISOLATED_LOCAL"].max_cross_workflow_handoffs != 0:
        errors.append("l0_must_disable_cross_workflow_handoffs")
    if by_id.get("L3_AGENTIC_FLEXIBLE") and by_id["L3_AGENTIC_FLEXIBLE"].max_cross_workflow_handoffs < 2:
        errors.append("l3_must_allow_multi_hop")
    l4 = by_id.get("L4_WHOLE_WORKFLOW_GATE_REPLAY")
    if l4 and l4.generation_condition:
        errors.append("l4_must_be_replay_not_generation")
    if l4 and l4.paired_replay_of != "L3_AGENTIC_FLEXIBLE":
        errors.append("l4_must_pair_to_l3")

    template = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    for placeholder in {
        "{owner_role}", "{agent_id}", "{local_actions}", "{current_action}",
        "{task_text}", "{visible_state}", "{external_agents}",
    }:
        if placeholder not in template:
            errors.append(f"prompt_missing_placeholder:{placeholder}")

    # The model sees business context, not the study's answer key.
    for token in (
        "UCA", "BR-01", "BR-02", "BR-03", "BR-04", "decision_id",
        "approval_paths", "source_record_ids", "analysis_stratum",
        "expected_relevant_bridge_ids",
    ):
        if token in template:
            errors.append(f"prompt_leaks_hidden_label:{token}")

    if int(experiment["repetitions_per_cell"]) != 10:
        errors.append("repetitions_must_remain_10_for_replication")
    if openai_replication_count() != 960:
        errors.append(f"openai_replication_count_must_be_960:{openai_replication_count()}")
    return tuple(errors)
