from dataclasses import dataclass, field

import pytest

from app.models import (
    IngestedJobDescription,
    JobDescriptionAnalysisRequest,
    StructuredJobDescription,
)
from app.services.jd import (
    JobDescriptionAnalysisError,
    StructuredJobDescriptionAnalyzer,
)


@dataclass
class FakeStructuredJdClient:
    responses: list[object]
    requests: list[JobDescriptionAnalysisRequest] = field(default_factory=list)

    def analyze(self, request: JobDescriptionAnalysisRequest) -> object:
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def ingested_jd() -> IngestedJobDescription:
    return IngestedJobDescription(
        raw_text="AI Engineer\nBuild reliable grounded agent systems.",
        raw_text_hash="a" * 64,
    )


def valid_response() -> dict[str, object]:
    return {
        "role": "AI Engineer",
        "company": "Example Labs",
        "seniority": "mid",
        "must_have_skills": ["Python", "LangGraph"],
        "preferred_skills": ["FastAPI"],
        "responsibilities": ["Build grounded agent systems"],
        "domain": "Developer tooling",
        "keywords": ["RAG", "evaluation"],
        "rejection_conditions": [],
        "location_constraints": ["India"],
        "experience_requirements": ["Production AI experience"],
    }


def test_jd_analyzer_injects_the_canonical_source_hash() -> None:
    payload = valid_response()
    client = FakeStructuredJdClient(responses=[payload])

    result = StructuredJobDescriptionAnalyzer(client=client).analyze(ingested_jd())

    assert result.role == "AI Engineer"
    assert result.raw_text_hash == "a" * 64
    assert "raw_text_hash" not in payload
    assert len(client.requests) == 1
    assert client.requests[0].raw_text == ingested_jd().raw_text
    assert client.requests[0].raw_text_hash == "a" * 64
    assert client.requests[0].schema_version == 1


def test_jd_analyzer_retries_a_response_with_a_foreign_hash() -> None:
    foreign_response = {
        **valid_response(),
        "raw_text_hash": "b" * 64,
    }
    client = FakeStructuredJdClient(
        responses=[foreign_response, valid_response()],
    )

    result = StructuredJobDescriptionAnalyzer(
        client=client,
        max_attempts=2,
    ).analyze(ingested_jd())

    assert result.raw_text_hash == "a" * 64
    assert len(client.requests) == 2


def test_jd_analyzer_accepts_an_echoed_canonical_source_hash() -> None:
    client = FakeStructuredJdClient(
        responses=[{**valid_response(), "raw_text_hash": "a" * 64}],
    )

    result = StructuredJobDescriptionAnalyzer(client=client).analyze(ingested_jd())

    assert result.raw_text_hash == "a" * 64
    assert len(client.requests) == 1


def test_jd_analyzer_validates_typed_responses_against_the_source_hash() -> None:
    foreign_response = StructuredJobDescription(
        role="AI Engineer",
        raw_text_hash="b" * 64,
    )
    canonical_response = StructuredJobDescription(
        role="AI Engineer",
        raw_text_hash="a" * 64,
    )
    client = FakeStructuredJdClient(
        responses=[foreign_response, canonical_response],
    )

    result = StructuredJobDescriptionAnalyzer(
        client=client,
        max_attempts=2,
    ).analyze(ingested_jd())

    assert result is canonical_response
    assert len(client.requests) == 2


def test_jd_analyzer_retries_transient_client_failures() -> None:
    client = FakeStructuredJdClient(
        responses=[RuntimeError("temporary provider failure"), valid_response()],
    )

    result = StructuredJobDescriptionAnalyzer(
        client=client,
        max_attempts=2,
    ).analyze(ingested_jd())

    assert result.company == "Example Labs"
    assert len(client.requests) == 2


def test_jd_analyzer_returns_a_sanitized_typed_failure_after_retry_exhaustion() -> None:
    client = FakeStructuredJdClient(
        responses=[
            {"role": "", "private_jd_text": "confidential hiring requirement"},
            "unstructured confidential hiring requirement",
        ],
    )

    with pytest.raises(JobDescriptionAnalysisError) as captured:
        StructuredJobDescriptionAnalyzer(
            client=client,
            max_attempts=2,
        ).analyze(ingested_jd())

    assert str(captured.value) == "structured JD analysis failed after 2 attempts"
    assert captured.value.attempts == 2
    assert "confidential" not in str(captured.value)
    assert len(client.requests) == 2


@pytest.mark.parametrize("max_attempts", [0, 4])
def test_jd_analyzer_rejects_an_unbounded_retry_policy(max_attempts: int) -> None:
    with pytest.raises(
        ValueError,
        match=r"^max_attempts must be between 1 and 3$",
    ):
        StructuredJobDescriptionAnalyzer(
            client=FakeStructuredJdClient(responses=[]),
            max_attempts=max_attempts,
        )
