from dataclasses import dataclass, field
import json

from unapproved_sum.protocol import load_models
from unapproved_sum.providers import AnthropicProvider, GeminiProvider, OpenAIProvider


@dataclass
class ODetails:
    reasoning_tokens: int = 3


@dataclass
class OUsage:
    input_tokens: int = 10
    output_tokens: int = 5
    total_tokens: int = 15
    output_tokens_details: ODetails = field(default_factory=ODetails)


@dataclass
class OResponse:
    output_text: str
    model: str
    id: str = "resp_openai"
    usage: OUsage = field(default_factory=OUsage)


class OResponses:
    def __init__(self): self.kwargs = []
    def create(self, **kwargs):
        self.kwargs.append(kwargs)
        return OResponse(json.dumps({"action":"stop","target_agent_id":None,"rationale":"Done.","confidence":0.8}), kwargs["model"])


class OClient:
    def __init__(self): self.responses = OResponses()


def test_openai_adapter_uses_structured_output_and_registry_settings():
    spec = load_models()["OAI_SOL"]
    client = OClient()
    provider = OpenAIProvider(spec, client=client)
    raw = provider.generate("x", task_id="T", condition_id="L", step_index=0, current_event_id="A")
    assert json.loads(raw)["action"] == "stop"
    kwargs = client.responses.kwargs[0]
    assert kwargs["reasoning"] == {"effort": "medium"}
    assert kwargs["temperature"] == 1.0
    assert kwargs["text"]["format"]["type"] == "json_schema"
    assert kwargs["store"] is False


class ABlock:
    type = "text"
    text = '{"action":"stop","target_agent_id":null,"rationale":"Done.","confidence":0.8}'


class AUsage:
    input_tokens = 11
    output_tokens = 7


class AResponse:
    content = [ABlock()]
    model = "claude-opus-5"
    id = "msg_anthropic"
    usage = AUsage()


class AMessages:
    def __init__(self): self.kwargs = []
    def create(self, **kwargs): self.kwargs.append(kwargs); return AResponse()


class AClient:
    def __init__(self): self.messages = AMessages()


def test_anthropic_adapter_uses_json_schema_output_config():
    spec = load_models()["CLAUDE_OPUS"]
    client = AClient()
    provider = AnthropicProvider(spec, client=client)
    raw = provider.generate("x", task_id="T", condition_id="L", step_index=0, current_event_id="A")
    assert json.loads(raw)["action"] == "stop"
    kwargs = client.messages.kwargs[0]
    assert kwargs["output_config"]["effort"] == "medium"
    assert kwargs["output_config"]["format"]["type"] == "json_schema"
    assert "temperature" not in kwargs
    assert "top_p" not in kwargs    

class GUsage:
    total_input_tokens = 12
    total_output_tokens = 8
    total_thought_tokens = 2
    total_tokens = 22


class GResponse:
    output_text = '{"action":"stop","target_agent_id":null,"rationale":"Done.","confidence":0.8}'
    model = "gemini-3.8-flash"
    id = "interaction_gemini"
    usage = GUsage()


class GInteractions:
    def __init__(self): self.kwargs = []
    def create(self, **kwargs): self.kwargs.append(kwargs); return GResponse()


class GClient:
    def __init__(self): self.interactions = GInteractions()


def test_gemini_adapter_uses_interactions_structured_output():
    spec = load_models()["GEMINI_FLASH"]
    client = GClient()
    provider = GeminiProvider(spec, client=client)
    raw = provider.generate("x", task_id="T", condition_id="L", step_index=0, current_event_id="A")
    assert json.loads(raw)["action"] == "stop"
    kwargs = client.interactions.kwargs[0]
    assert kwargs["generation_config"]["thinking_level"] == "medium"
    assert "temperature" not in kwargs["generation_config"]
    assert "top_p" not in kwargs["generation_config"]
    assert kwargs["response_format"]["mime_type"] == "application/json"
