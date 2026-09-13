from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from .models import ActionEvent, DecisionRule


def causal_edges(events: Iterable[ActionEvent]) -> tuple[tuple[str, str], ...]:
    """Infer causal edges only from produced state consumed by later actions."""

    ordered = list(events)
    edges: list[tuple[str, str]] = []
    for index, left in enumerate(ordered):
        for right in ordered[index + 1 :]:
            if left.produces.intersection(right.consumes):
                edges.append((left.event_id, right.event_id))
    return tuple(edges)


def accumulated_state(events: Iterable[ActionEvent]) -> frozenset[str]:
    state: set[str] = set()
    for event in events:
        state.update(event.produces)
    return frozenset(state)


def accumulated_totals(events: Iterable[ActionEvent]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for event in events:
        for key, value in event.quantitative_effects:
            totals[key] += value
    return dict(totals)


def compiled_decisions(
    events: Iterable[ActionEvent],
    rules: Iterable[DecisionRule],
) -> tuple[str, ...]:
    """Return institutional decisions instantiated by combined state/effects."""

    events = tuple(events)
    state = accumulated_state(events)
    totals = accumulated_totals(events)

    compiled: list[str] = []
    for rule in rules:
        state_ok = rule.required_state.issubset(state)
        totals_ok = all(totals.get(key, 0.0) >= minimum for key, minimum in rule.minimum_totals)
        if state_ok and totals_ok:
            compiled.append(rule.decision_id)
    return tuple(compiled)
