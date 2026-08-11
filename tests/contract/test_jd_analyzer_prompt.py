"""Contracts for the versioned structured job-description prompt and adapter."""

from dataclasses import dataclass, field

import pytest

from app.models import JobDescriptionAnalysisRequest


def _request() -> JobDescriptionAnalysisRequest:
    return JobDescriptionAnalysisRequest(
        raw_text=(
            "AI Engineer at Example Labs. Build production Python and LangGraph "
            "agent workflows with FastAPI, RAG, vector databases, and evaluation."
        ),
        raw_text_hash="a" * 64,
    )


@pytest.mark.contract
def test_jd_analyzer_prompt_is_versioned_and_deterministic() -> None:
    from app.prompts import jd_analyzer_v1

    request = _request()
    assert "v1" in jd_analyzer_v1.PROMPT_VERSION
    assert jd_analyzer_v1.render(request) == jd_analyzer_v1.render(request)


@pytest.mark.contract
def test_jd_analyzer_prompt_contains_source_and_provenance_hash() -> None:
    from app.prompts import jd_analyzer_v1

    rendered = jd_analyzer_v1.render(_request())
    assert "AI Engineer at Example Labs" in rendered
    assert "a" * 64 in rendered
    assert "schema_version" in rendered


@pytest.mark.contract
def test_jd_analyzer_prompt_requires_complete_json_schema() -> None:
    from app.prompts import jd_analyzer_v1

    rendered = jd_analyzer_v1.render(_request()).lower()
    required_fields = (
        "role",
        "company",
        "seniority",
        "must_have_skills",
        "preferred_skills",
        "responsibilities",
        "domain",
        "keywords",
        "rejection_conditions",
        "location_constraints",
        "experience_requirements",
        "raw_text_hash",
    )
    assert all(field in rendered for field in required_fields)
    assert "return only json" in rendered
    assert "do not invent" in rendered


@dataclass
class _CapturingBackend:
    response: object
    prompts: list[str] = field(default_factory=list)

    def complete(self, prompt: str) -> object:
        self.prompts.append(prompt)
        return self.response


@pytest.mark.contract
def test_prompt_structured_jd_client_uses_versioned_prompt() -> None:
    from app.prompts import jd_analyzer_v1
    from app.services.providers import PromptStructuredJdClient

    backend = _CapturingBackend(response={"role": "AI Engineer"})
    request = _request()

    result = PromptStructuredJdClient(backend=backend).analyze(request)

    assert result == {"role": "AI Engineer"}
    assert backend.prompts == [jd_analyzer_v1.render(request)]


@pytest.mark.contract
def test_prompt_structured_jd_client_propagates_backend_errors() -> None:
    from app.services.providers import PromptStructuredJdClient

    class _FailingBackend:
        def complete(self, prompt: str) -> object:
            raise ConnectionError("provider unavailable")

    with pytest.raises(ConnectionError, match="provider unavailable"):
        PromptStructuredJdClient(backend=_FailingBackend()).analyze(_request())
