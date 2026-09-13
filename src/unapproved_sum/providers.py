from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import os
import time
from typing import Any

from .protocol import ModelSpec


# Keep the schema deliberately small. The Python parser still checks the semantic rules
# (for example, confidence must be between 0 and 1 and a handoff target must be offered).
# Avoiding vendor-specific JSON Schema features makes the same response contract usable
# with OpenAI, Anthropic, and Gemini.
AGENT_CHOICE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "action": {"type": "string", "enum": ["stop", "handoff"]},
        "target_agent_id": {"type": ["string", "null"]},
        "rationale": {"type": "string"},
        "confidence": {"type": "number"},
    },
    "required": ["action", "target_agent_id", "rationale", "confidence"],
}


@dataclass(frozen=True)
class ProviderCallAudit:
    provider: str
    task_id: str
    condition_id: str
    step_index: int
    current_event_id: str
    configured_model_id: str
    response_model_id: str | None
    response_id: str | None
    prompt_sha256: str
    response_sha256: str
    input_tokens: int | None
    output_tokens: int | None
    reasoning_tokens: int | None
    total_tokens: int | None
    latency_ms: int
    attempt: int
    timestamp_utc: str


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _int_attr(obj: Any, *names: str) -> int | None:
    if obj is None:
        return None
    for name in names:
        value = getattr(obj, name, None)
        if isinstance(value, int):
            return value
    return None


class BaseProvider:
    def __init__(self, model_spec: ModelSpec, *, max_attempts: int = 3):
        if max_attempts < 1:
            raise ValueError("max_attempts_must_be_positive")
        self.model_spec = model_spec
        self.max_attempts = max_attempts
        self.audit_log: list[ProviderCallAudit] = []
        self.error_log: list[dict[str, Any]] = []

    def _call(self, prompt: str) -> tuple[str, dict[str, Any]]:
        raise NotImplementedError

    def generate(
        self,
        prompt: str,
        *,
        task_id: str,
        condition_id: str,
        step_index: int,
        current_event_id: str,
    ) -> str:
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            started = time.perf_counter()
            try:
                raw, meta = self._call(prompt)
                latency_ms = int((time.perf_counter() - started) * 1000)
                raw = raw.strip()
                if not raw:
                    raise ValueError("empty_model_output")
                self.audit_log.append(
                    ProviderCallAudit(
                        provider=self.model_spec.provider,
                        task_id=task_id,
                        condition_id=condition_id,
                        step_index=step_index,
                        current_event_id=current_event_id,
                        configured_model_id=self.model_spec.model_id,
                        response_model_id=meta.get("response_model_id"),
                        response_id=meta.get("response_id"),
                        prompt_sha256=sha256_text(prompt),
                        response_sha256=sha256_text(raw),
                        input_tokens=meta.get("input_tokens"),
                        output_tokens=meta.get("output_tokens"),
                        reasoning_tokens=meta.get("reasoning_tokens"),
                        total_tokens=meta.get("total_tokens"),
                        latency_ms=latency_ms,
                        attempt=attempt,
                        timestamp_utc=datetime.now(timezone.utc).isoformat(),
                    )
                )
                return raw
            except Exception as exc:
                last_error = exc
                self.error_log.append(
                    {
                        "provider": self.model_spec.provider,
                        "task_id": task_id,
                        "condition_id": condition_id,
                        "step_index": step_index,
                        "current_event_id": current_event_id,
                        "model_id": self.model_spec.model_id,
                        "attempt": attempt,
                        "error_type": type(exc).__name__,
                        "error": str(exc)[:1000],
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    }
                )
                if attempt < self.max_attempts:
                    time.sleep(1.5 * attempt)
        assert last_error is not None
        raise RuntimeError(
            f"provider_failed:{self.model_spec.provider}:{self.model_spec.model_id}:"
            f"{task_id}:{condition_id}:{current_event_id}"
        ) from last_error

    def audit_dicts(self) -> list[dict[str, Any]]:
        return [asdict(item) for item in self.audit_log]


class OpenAIProvider(BaseProvider):
    def __init__(self, model_spec: ModelSpec, *, client: Any | None = None, max_attempts: int = 3):
        if model_spec.provider != "openai":
            raise ValueError(f"wrong_provider_for_openai_adapter:{model_spec.provider}")
        super().__init__(model_spec, max_attempts=max_attempts)
        if client is None:
            if not os.getenv("OPENAI_API_KEY"):
                raise RuntimeError("OPENAI_API_KEY is not set")
            from openai import OpenAI

            client = OpenAI()
        self.client = client

    def _call(self, prompt: str) -> tuple[str, dict[str, Any]]:
        settings = self.model_spec.settings
        kwargs: dict[str, Any] = {
            "model": self.model_spec.model_id,
            "input": prompt,
            "reasoning": {"effort": settings["reasoning_effort"]},
            "temperature": float(settings["temperature"]),
            "max_output_tokens": int(settings["max_output_tokens"]),
            "store": bool(settings.get("store", False)),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "enterprise_agent_choice",
                    "strict": True,
                    "schema": AGENT_CHOICE_SCHEMA,
                }
            },
        }
        if settings.get("top_p") is not None:
            kwargs["top_p"] = float(settings["top_p"])
        response = self.client.responses.create(**kwargs)
        raw = str(getattr(response, "output_text", "") or "")
        usage = getattr(response, "usage", None)
        details = getattr(usage, "output_tokens_details", None) if usage else None
        return raw, {
            "response_model_id": getattr(response, "model", None),
            "response_id": getattr(response, "id", None),
            "input_tokens": _int_attr(usage, "input_tokens"),
            "output_tokens": _int_attr(usage, "output_tokens"),
            "reasoning_tokens": _int_attr(details, "reasoning_tokens"),
            "total_tokens": _int_attr(usage, "total_tokens"),
        }


class AnthropicProvider(BaseProvider):
    def __init__(self, model_spec: ModelSpec, *, client: Any | None = None, max_attempts: int = 3):
        if model_spec.provider != "anthropic":
            raise ValueError(f"wrong_provider_for_anthropic_adapter:{model_spec.provider}")
        super().__init__(model_spec, max_attempts=max_attempts)
        if client is None:
            if not os.getenv("ANTHROPIC_API_KEY"):
                raise RuntimeError("ANTHROPIC_API_KEY is not set")
            from anthropic import Anthropic

            client = Anthropic()
        self.client = client

    def _call(self, prompt: str) -> tuple[str, dict[str, Any]]:
        settings = self.model_spec.settings
        kwargs: dict[str, Any] = {
            "model": self.model_spec.model_id,
            "max_tokens": int(settings["max_output_tokens"]),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": float(settings["temperature"]),
            "output_config": {
                "effort": settings["effort"],
                "format": {"type": "json_schema", "schema": AGENT_CHOICE_SCHEMA},
            },
        }
        if settings.get("top_p") is not None:
            kwargs["top_p"] = float(settings["top_p"])
        response = self.client.messages.create(**kwargs)
        texts = [getattr(block, "text", "") for block in response.content if getattr(block, "type", None) == "text"]
        raw = "".join(texts)
        usage = getattr(response, "usage", None)
        details = getattr(usage, "output_tokens_details", None) if usage else None
        input_tokens = _int_attr(usage, "input_tokens")
        output_tokens = _int_attr(usage, "output_tokens")
        total_tokens = None
        if input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens
        return raw, {
            "response_model_id": getattr(response, "model", None),
            "response_id": getattr(response, "id", None),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "reasoning_tokens": _int_attr(details, "thinking_tokens"),
            "total_tokens": total_tokens,
        }


class GeminiProvider(BaseProvider):
    def __init__(self, model_spec: ModelSpec, *, client: Any | None = None, max_attempts: int = 3):
        if model_spec.provider != "gemini":
            raise ValueError(f"wrong_provider_for_gemini_adapter:{model_spec.provider}")
        super().__init__(model_spec, max_attempts=max_attempts)
        if client is None:
            if not os.getenv("GEMINI_API_KEY"):
                raise RuntimeError("GEMINI_API_KEY is not set")
            from google import genai

            client = genai.Client()
        self.client = client

    def _call(self, prompt: str) -> tuple[str, dict[str, Any]]:
        settings = self.model_spec.settings
        # Gemini 3.8 Flash's current Interactions API migration guidance says to
        # remove sampling parameters such as temperature/top_p and control reasoning
        # with thinking_level instead. Keep this adapter aligned with that native API.
        generation_config: dict[str, Any] = {
            "thinking_level": settings["thinking_level"],
            "max_output_tokens": int(settings["max_output_tokens"]),
        }
        interaction = self.client.interactions.create(
            model=self.model_spec.model_id,
            input=prompt,
            generation_config=generation_config,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": AGENT_CHOICE_SCHEMA,
            },
        )
        usage = getattr(interaction, "usage", None)
        return str(getattr(interaction, "output_text", "") or ""), {
            "response_model_id": getattr(interaction, "model", None),
            "response_id": getattr(interaction, "id", None),
            "input_tokens": _int_attr(usage, "total_input_tokens", "input_tokens"),
            "output_tokens": _int_attr(usage, "total_output_tokens", "output_tokens"),
            "reasoning_tokens": _int_attr(usage, "total_thought_tokens", "thought_tokens"),
            "total_tokens": _int_attr(usage, "total_tokens"),
        }


def make_provider(model_spec: ModelSpec, *, max_attempts: int = 3, client: Any | None = None) -> BaseProvider:
    if model_spec.provider == "openai":
        return OpenAIProvider(model_spec, client=client, max_attempts=max_attempts)
    if model_spec.provider == "anthropic":
        return AnthropicProvider(model_spec, client=client, max_attempts=max_attempts)
    if model_spec.provider == "gemini":
        return GeminiProvider(model_spec, client=client, max_attempts=max_attempts)
    raise ValueError(f"unsupported_provider:{model_spec.provider}")
