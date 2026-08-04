import pytest
from pydantic import ValidationError

from app.models import StructuredJobDescription


def test_structured_jd_rejects_missing_role() -> None:
    with pytest.raises(ValidationError):
        StructuredJobDescription(raw_text_hash="0" * 64)


def test_structured_jd_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        StructuredJobDescription(
            role="AI Engineer",
            raw_text_hash="0" * 64,
            invented_requirement="five years of teleportation",
        )


@pytest.mark.parametrize(
    "raw_text_hash",
    ["", "not-a-hash", "A" * 64, "0" * 63, "0" * 65],
)
def test_structured_jd_requires_a_canonical_sha256_hash(raw_text_hash: str) -> None:
    with pytest.raises(ValidationError):
        StructuredJobDescription(
            role="AI Engineer",
            raw_text_hash=raw_text_hash,
        )


def test_structured_jd_preserves_requirement_groups() -> None:
    job = StructuredJobDescription(
        role="Applied AI Engineer",
        company="Example Labs",
        seniority="mid",
        must_have_skills=("Python", "LangGraph"),
        preferred_skills=("FastAPI",),
        responsibilities=("Build grounded agent workflows",),
        domain="Developer tooling",
        keywords=("RAG", "evaluation"),
        rejection_conditions=("No production Python experience",),
        location_constraints=("India",),
        experience_requirements=("2+ years building AI systems",),
        raw_text_hash="a" * 64,
    )

    assert job.must_have_skills == ("Python", "LangGraph")
    assert job.seniority == "mid"
    assert job.raw_text_hash == "a" * 64
