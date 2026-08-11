"""Contract tests for Gemini backend adapter."""

import json
import sys
import time
from types import ModuleType, SimpleNamespace

import pytest

from app.services.providers import GeminiCompletionsBackend


@pytest.mark.contract
def test_gemini_backend_initialization_requires_api_key() -> None:
    with pytest.raises(ValueError, match="api_key must not be empty"):
        GeminiCompletionsBackend(api_key="", model_name="gemini-1.5-flash")


@pytest.mark.contract
def test_gemini_backend_strips_json_markdown_fences() -> None:
    backend = GeminiCompletionsBackend(
        api_key="fake_key", model_name="gemini-1.5-flash"
    )
    raw_text = '```json\n{"resume_id": "r.001", "target_role": "AI Engineer"}\n```'
    cleaned = backend._clean_json_text(raw_text)
    assert json.loads(cleaned) == {"resume_id": "r.001", "target_role": "AI Engineer"}


@pytest.mark.contract
def test_gemini_backend_reserves_enough_tokens_for_rich_resume_json() -> None:
    """Five experiences and six projects must not be truncated by configuration."""
    assert GeminiCompletionsBackend._MAX_OUTPUT_TOKENS >= 8_192


@pytest.mark.contract
def test_gemini_backend_honors_provider_retry_delay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RetryableClientError(Exception):
        status_code = 429
        code = 429
        message = "Quota window exceeded. Please retry in 25.111824651s."

    class RetryableServerError(Exception):
        pass

    responses: list[object] = [
        RetryableClientError(),
        SimpleNamespace(text='{"status": "ok"}'),
    ]

    class FakeModels:
        def generate_content(self, **_: object) -> object:
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

    class FakeClient:
        models = FakeModels()

    google_module = ModuleType("google")
    genai_module = ModuleType("google.genai")
    genai_types_module = ModuleType("google.genai.types")
    genai_errors_module = ModuleType("google.genai.errors")
    genai_module.Client = lambda **_: FakeClient()  # type: ignore[attr-defined]
    genai_types_module.GenerateContentConfig = lambda **kwargs: kwargs  # type: ignore[attr-defined]
    genai_errors_module.ClientError = RetryableClientError  # type: ignore[attr-defined]
    genai_errors_module.ServerError = RetryableServerError  # type: ignore[attr-defined]
    genai_module.types = genai_types_module  # type: ignore[attr-defined]
    google_module.genai = genai_module  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)
    monkeypatch.setitem(sys.modules, "google.genai.types", genai_types_module)
    monkeypatch.setitem(sys.modules, "google.genai.errors", genai_errors_module)

    sleep_seconds: list[float] = []
    monkeypatch.setattr(time, "sleep", sleep_seconds.append)

    backend = GeminiCompletionsBackend(api_key="fake", model_name="gemini-flash")

    assert backend.complete("prompt") == {"status": "ok"}
    assert sleep_seconds == [26]
