import json

import pytest

import app.services.llm_client as llm_client_module
from app.services.llm_client import LLMClientError, OpenAICompatibleClient


class FakeDelta:
    def __init__(self, content=None, reasoning_content=None):
        self.content = content
        self.reasoning_content = reasoning_content


class FakeChoice:
    def __init__(self, delta):
        self.delta = delta


class FakeChunk:
    def __init__(self, content=None, reasoning_content=None):
        self.choices = [FakeChoice(FakeDelta(content=content, reasoning_content=reasoning_content))]


class FakeStream:
    def __init__(self, chunks):
        self._chunks = chunks
        self.closed = False

    def __iter__(self):
        return iter(self._chunks)

    def close(self):
        self.closed = True


class FakeChatCompletions:
    def __init__(self, *, chunks=None, exc=None):
        self._chunks = chunks or []
        self._exc = exc
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._exc is not None:
            raise self._exc
        return FakeStream(self._chunks)


class FakeChat:
    def __init__(self, completions):
        self.completions = completions


class FakeOpenAIClient:
    def __init__(self, *, chunks=None, exc=None):
        self.completions = FakeChatCompletions(chunks=chunks, exc=exc)
        self.chat = FakeChat(self.completions)


def test_build_messages_merges_instruction_and_input():
    client = OpenAICompatibleClient()

    messages = client._build_messages("请抽取三元组", "这里是一条文本")

    assert messages == [{"role": "user", "content": "请抽取三元组\n\n这里是一条文本"}]


def test_build_request_options_injects_structured_defaults_for_v32():
    client = OpenAICompatibleClient()

    options = client._build_request_options(
        "https://api.siliconflow.cn/v1",
        "deepseek-ai/DeepSeek-V3.2",
        "请抽取三元组并输出 JSON 数组。",
        None,
    )

    assert options["temperature"] == 0.6
    assert options["top_p"] == 0.95
    assert options["max_tokens"] == 256
    assert "extra_body" not in options


def test_build_request_options_deep_merges_provider_overrides():
    client = OpenAICompatibleClient()

    options = client._build_request_options(
        "https://api.siliconflow.cn/v1",
        "deepseek-ai/DeepSeek-R1",
        "请抽取三元组并输出 JSON 数组。",
        {
            "temperature": 0.2,
            "max_tokens": 512,
            "extra_body": {"thinking_budget": 64, "trace_id": "abc"},
        },
    )

    assert options["temperature"] == 0.2
    assert options["top_p"] == 0.95
    assert options["max_tokens"] == 512
    assert options["extra_body"] == {"thinking_budget": 64, "trace_id": "abc"}


def test_call_aggregates_stream_chunks(monkeypatch):
    fake_client = FakeOpenAIClient(chunks=[FakeChunk(content="前半段"), FakeChunk(content="后半段")])

    monkeypatch.setattr(
        "app.services.llm_client.OpenAI",
        lambda **kwargs: fake_client,
    )

    client = OpenAICompatibleClient()
    raw_response = client.call(
        base_url="https://api.siliconflow.cn/v1",
        api_key="sk-test",
        model_name="deepseek-ai/DeepSeek-V3.2",
        instruction="请抽取三元组并输出 JSON 数组。",
        input_text="示例输入",
        timeout_seconds=5,
    )

    payload = json.loads(raw_response)

    assert payload["output"] == "前半段后半段"
    assert payload["provider_response"]["stream"] is True
    assert payload["provider_response"]["chunk_count"] == 2
    assert payload["provider_response"]["request_payload"]["max_tokens"] == 256


def test_call_error_message_contains_required_diagnostics(monkeypatch):
    fake_client = FakeOpenAIClient(exc=ValueError("boom"))

    monkeypatch.setattr(
        "app.services.llm_client.OpenAI",
        lambda **kwargs: fake_client,
    )

    client = OpenAICompatibleClient()

    with pytest.raises(LLMClientError) as exc_info:
        client.call(
            base_url="https://api.siliconflow.cn/v1",
            api_key="sk-test",
            model_name="deepseek-ai/DeepSeek-V3.2",
            instruction="请抽取三元组并输出 JSON 数组。",
            input_text="示例输入",
            timeout_seconds=5,
        )

    assert exc_info.value.error_code == "MODEL_REQUEST_FAILED"
    assert "MODEL_REQUEST_FAILED" in exc_info.value.message
    assert "exception=ValueError" in exc_info.value.message
    assert "model=deepseek-ai/DeepSeek-V3.2" in exc_info.value.message
    assert "request_url=https://api.siliconflow.cn/v1/chat/completions" in exc_info.value.message


def test_mock_client_maps_military_triples(monkeypatch, tmp_path):
    dataset_path = tmp_path / "mock_dataset.json"
    sample_output = json.dumps(
        [
            {
                "head": "MQ-8C",
                "head_type": "Asset",
                "relation": "deployed_by",
                "tail": "美国海军",
                "tail_type": "Actor",
            }
        ],
        ensure_ascii=False,
    )
    dataset_path.write_text(
        json.dumps(
            [
                {
                    "instruction": "unused",
                    "input": "样例输入",
                    "output": sample_output,
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(llm_client_module, "MOCK_DATASET_PATH", dataset_path)
    llm_client_module._load_mock_extract_dataset.cache_clear()
    try:
        client = llm_client_module.MockCompatibleClient()
        raw_response = client.call(
            base_url="mock://extract",
            api_key="sk-test",
            model_name="mock-model",
            instruction="ignored",
            input_text="样例输入",
            timeout_seconds=5,
        )
    finally:
        llm_client_module._load_mock_extract_dataset.cache_clear()

    payload = json.loads(raw_response)
    triples = json.loads(payload["output"])
    assert triples == [
        {
            "subject": "MQ-8C",
            "subject_type": "Asset",
            "predicate": "deployed_by",
            "object": "美国海军",
            "object_type": "Actor",
        }
    ]
    assert payload["provider_response"]["mode"] == "dataset_exact"


def test_mock_client_returns_empty_array_when_input_not_found(monkeypatch, tmp_path):
    dataset_path = tmp_path / "mock_dataset.json"
    dataset_path.write_text(
        json.dumps(
            [
                {
                    "instruction": "unused",
                    "input": "命中输入",
                    "output": "[]",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(llm_client_module, "MOCK_DATASET_PATH", dataset_path)
    llm_client_module._load_mock_extract_dataset.cache_clear()
    try:
        client = llm_client_module.MockCompatibleClient()
        raw_response = client.call(
            base_url="mock://extract",
            api_key="sk-test",
            model_name="mock-model",
            instruction="ignored",
            input_text="未命中输入",
            timeout_seconds=5,
        )
    finally:
        llm_client_module._load_mock_extract_dataset.cache_clear()

    payload = json.loads(raw_response)
    assert payload["output"] == "[]"
    assert payload["provider_response"]["mode"] == "dataset_miss"
