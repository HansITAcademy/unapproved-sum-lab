"""Optional live pilot adapter for the distinct downstream-agent choice schema."""
from __future__ import annotations

import os
from typing import Any


FOLLOWUP_CHOICE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "choice": {"type": "string", "enum": ["execute", "decline", "handoff", "stop"]},
        "target_event_id": {"type": ["string", "null"]},
        "reason": {"type": "string"},
    },
    "required": ["choice", "target_event_id", "reason"],
}


class OpenAIFollowupAgent:
    """Stateless role calls: each recipient chooses without inherited chat history."""

    def __init__(self, model_id: str, *, client: Any | None = None):
        if client is None:
            if not os.getenv("OPENAI_API_KEY"):
                raise RuntimeError("OPENAI_API_KEY is not set")
            from openai import OpenAI
            client = OpenAI()
        self.client = client
        self.model_id = model_id
        self.calls: list[dict] = []

    def choose(self, prompt: str, *, agent_id: str, task_id: str, phase: str) -> str:
        response = self.client.responses.create(
            model=self.model_id,
            input=prompt,
            reasoning={"effort": "medium"},
            max_output_tokens=512,
            store=False,
            text={"format": {"type": "json_schema", "name": "followup_role_choice",
                             "strict": True, "schema": FOLLOWUP_CHOICE_SCHEMA}},
        )
        raw = str(getattr(response, "output_text", "") or "")
        if not raw.strip():
            raise RuntimeError("empty_followup_model_output")
        self.calls.append({"agent_id": agent_id, "task_id": task_id, "phase": phase,
                           "model_id": self.model_id, "response_id": getattr(response, "id", None),
                           "prompt": prompt, "response": raw})
        return raw
