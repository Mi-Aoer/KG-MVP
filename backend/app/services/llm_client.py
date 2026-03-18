import json
import time
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MOCK_DATASET_PATH = PROJECT_ROOT / "data" / "CMeIE-V2_测试用数据集.json"


class LLMClientError(Exception):
    def __init__(self, error_code: str, message: str | None = None):
        self.error_code = error_code
        self.message = message or error_code
        super().__init__(self.message)


class OpenAICompatibleClient:
    def _normalize_base_url(self, base_url: str) -> str:
        normalized = base_url.rstrip("/")
        if normalized.endswith("/chat/completions"):
            normalized = normalized[: -len("/chat/completions")]
        return normalized

    def _build_request_url(self, base_url: str) -> str:
        return f"{self._normalize_base_url(base_url)}/chat/completions"

    def _build_messages(self, instruction: str, input_text: str) -> list[dict[str, str]]:
        instruction_text = instruction.strip()
        if instruction_text:
            content = f"{instruction_text}\n\n{input_text}"
        else:
            content = input_text
        return [{"role": "user", "content": content}]

    def _build_request_options(
        self,
        base_url: str,
        model_name: str,
        instruction: str,
        provider_options: dict | None,
    ) -> dict:
        normalized_base_url = self._normalize_base_url(base_url).lower()
        normalized_model_name = model_name.lower()
        options: dict = {}
        if "siliconflow.cn" in normalized_base_url and "deepseek-r1" in normalized_model_name:
            options.update(
                {
                    "temperature": 0.6,
                    "top_p": 0.95,
                    "extra_body": {"thinking_budget": 128},
                }
            )
            lowered_instruction = instruction.lower()
            if "json" in lowered_instruction or "三元组" in instruction:
                options["max_tokens"] = 256
        if provider_options:
            options.update(deepcopy(provider_options))
        return options

    def _truncate_text(self, value: str | None, *, limit: int = 400) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if len(normalized) <= limit:
            return normalized
        return f"{normalized[:limit]}..."

    def _build_error_message(
        self,
        *,
        error_code: str,
        request_url: str,
        model_name: str,
        exc: Exception,
        status_code: int | None = None,
        response_text: str | None = None,
    ) -> str:
        parts = [
            error_code,
            f"exception={type(exc).__name__}",
            f"model={model_name}",
            f"request_url={request_url}",
        ]
        if status_code is not None:
            parts.append(f"status_code={status_code}")
        cause = exc.__cause__
        if cause is not None:
            parts.append(f"cause={type(cause).__name__}:{cause}")
        elif str(exc):
            parts.append(f"detail={exc}")
        response_preview = self._truncate_text(response_text)
        if response_preview is not None:
            parts.append(f"response_preview={response_preview}")
        return " | ".join(parts)

    def call(
        self,
        *,
        base_url: str,
        api_key: str,
        model_name: str,
        instruction: str,
        input_text: str,
        timeout_seconds: int,
        provider_options: dict | None = None,
    ) -> str:
        normalized_base_url = self._normalize_base_url(base_url)
        request_url = self._build_request_url(base_url)
        messages = self._build_messages(instruction, input_text)
        request_options = self._build_request_options(
            base_url,
            model_name,
            instruction,
            provider_options,
        )
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": True,
            **request_options,
        }

        try:
            client = OpenAI(
                api_key=api_key,
                base_url=normalized_base_url,
                timeout=timeout_seconds,
                max_retries=0,
            )
            stream = client.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=True,
                **request_options,
            )
            content_chunks: list[str] = []
            reasoning_chunks: list[str] = []
            chunk_count = 0
            started_at = time.monotonic()
            for chunk in stream:
                if time.monotonic() - started_at > timeout_seconds:
                    if hasattr(stream, "close"):
                        stream.close()
                    raise LLMClientError(
                        "MODEL_TIMEOUT",
                        self._build_error_message(
                            error_code="MODEL_TIMEOUT",
                            request_url=request_url,
                            model_name=model_name,
                            exc=TimeoutError(
                                f"stream exceeded timeout_seconds={timeout_seconds}"
                            ),
                        ),
                    )
                chunk_count += 1
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    content_chunks.append(delta.content)
                reasoning_content = getattr(delta, "reasoning_content", None)
                if reasoning_content:
                    reasoning_chunks.append(reasoning_content)
        except LLMClientError:
            raise
        except APITimeoutError as exc:
            raise LLMClientError(
                "MODEL_TIMEOUT",
                self._build_error_message(
                    error_code="MODEL_TIMEOUT",
                    request_url=request_url,
                    model_name=model_name,
                    exc=exc,
                ),
            ) from exc
        except APIStatusError as exc:
            status_code = getattr(exc, "status_code", None)
            if status_code in {401, 403}:
                error_code = "MODEL_AUTH_FAILED"
            elif status_code is not None and status_code >= 500:
                error_code = "MODEL_SERVER_ERROR"
            else:
                error_code = "MODEL_REQUEST_FAILED"
            response_text = None
            if getattr(exc, "response", None) is not None:
                response_text = exc.response.text
            raise LLMClientError(
                error_code,
                self._build_error_message(
                    error_code=error_code,
                    request_url=request_url,
                    model_name=model_name,
                    exc=exc,
                    status_code=status_code,
                    response_text=response_text,
                ),
            ) from exc
        except APIConnectionError as exc:
            raise LLMClientError(
                "MODEL_NETWORK_ERROR",
                self._build_error_message(
                    error_code="MODEL_NETWORK_ERROR",
                    request_url=request_url,
                    model_name=model_name,
                    exc=exc,
                ),
            ) from exc
        except Exception as exc:
            raise LLMClientError(
                "MODEL_REQUEST_FAILED",
                self._build_error_message(
                    error_code="MODEL_REQUEST_FAILED",
                    request_url=request_url,
                    model_name=model_name,
                    exc=exc,
                ),
            ) from exc

        content = "".join(content_chunks)
        reasoning_content = "".join(reasoning_chunks)
        output = content or reasoning_content
        if not output:
            raise LLMClientError(
                "INVALID_PROVIDER_RESPONSE",
                self._build_error_message(
                    error_code="INVALID_PROVIDER_RESPONSE",
                    request_url=request_url,
                    model_name=model_name,
                    exc=ValueError("empty stream response"),
                ),
            )

        return json.dumps(
            {
                "output": output,
                "provider_response": {
                    "stream": True,
                    "chunk_count": chunk_count,
                    "request_url": request_url,
                    "message": {
                        "content": content,
                        "reasoning_content": reasoning_content or None,
                    },
                    "request_payload": payload,
                },
            },
            ensure_ascii=False,
        )


@lru_cache(maxsize=1)
def _load_mock_extract_dataset() -> dict[str, str]:
    if not MOCK_DATASET_PATH.exists():
        return {}

    try:
        raw_items = json.loads(MOCK_DATASET_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(raw_items, list):
        return {}

    dataset: dict[str, str] = {}
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        input_text = item.get("input")
        output_text = item.get("output")
        if not isinstance(input_text, str) or not isinstance(output_text, str):
            continue
        dataset[input_text] = output_text

    return dataset


class MockCompatibleClient:
    def _match_dataset_output(self, input_text: str) -> tuple[str | None, str]:
        dataset = _load_mock_extract_dataset()
        if input_text in dataset:
            return dataset[input_text], "dataset_exact"

        normalized_input = input_text.strip()
        if normalized_input in dataset:
            return dataset[normalized_input], "dataset_trimmed"

        return None, "dataset_miss"

    def call(
        self,
        *,
        base_url: str,
        api_key: str,
        model_name: str,
        instruction: str,
        input_text: str,
        timeout_seconds: int,
        provider_options: dict | None = None,
    ) -> str:
        del api_key
        del model_name
        del provider_options
        del timeout_seconds
        del instruction
        if base_url == "mock://extract":
            output, mock_mode = self._match_dataset_output(input_text)
            if output is None:
                output = "[]"
        else:
            output = "[]"
            mock_mode = "empty"
        return json.dumps(
            {
                "output": output,
                "provider_response": {
                    "mock": True,
                    "base_url": base_url,
                    "mode": mock_mode,
                    "dataset_path": str(MOCK_DATASET_PATH),
                },
            },
            ensure_ascii=False,
        )


def get_llm_client(base_url: str):
    if base_url.startswith("mock://"):
        return MockCompatibleClient()
    return OpenAICompatibleClient()
