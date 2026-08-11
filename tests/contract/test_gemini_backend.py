"""Contract tests for Gemini backend adapter."""

import json
import pytest

from app.services.providers import GeminiCompletionsBackend


@pytest.mark.contract
def test_gemini_backend_initialization_requires_api_key() -> None:
    with pytest.raises(ValueError, match="api_key must not be empty"):
        GeminiCompletionsBackend(api_key="", model_name="gemini-1.5-flash")


@pytest.mark.contract
def test_gemini_backend_strips_json_markdown_fences() -> None:
    backend = GeminiCompletionsBackend(api_key="fake_key", model_name="gemini-1.5-flash")
    raw_text = "```json\n{\"resume_id\": \"r.001\", \"target_role\": \"AI Engineer\"}\n```"
    cleaned = backend._clean_json_text(raw_text)
    assert json.loads(cleaned) == {"resume_id": "r.001", "target_role": "AI Engineer"}


@pytest.mark.contract
def test_gemini_backend_reserves_enough_tokens_for_rich_resume_json() -> None:
    """Five experiences and six projects must not be truncated by configuration."""
    assert GeminiCompletionsBackend._MAX_OUTPUT_TOKENS >= 8_192
