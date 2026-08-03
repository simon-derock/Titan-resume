from datetime import date

import pytest
from pydantic import ValidationError

from app.models import (
    EvidenceRecord,
    EvidenceText,
    ResumeBullet,
    ResumeContent,
    ResumeEntry,
    UnknownEvidenceError,
    validate_resume_content_evidence,
)


def evidence(evidence_id: str) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        source_type="project",
        source_id="titan",
        claim="Built a deterministic resume compiler.",
        skills=("Python",),
        confidence=1.0,
        allowed_for_resume=True,
        last_verified_at=date(2026, 8, 3),
    )


def resume_content(evidence_id: str = "project.titan.001") -> ResumeContent:
    bullet = ResumeBullet(
        element_id="projects.titan.bullet_1",
        text="Built a deterministic resume compiler.",
        evidence_ids=(evidence_id,),
    )
    return ResumeContent(
        resume_id="resume.ai_engineer.001",
        target_role="AI Engineer",
        summary=EvidenceText(
            element_id="summary",
            text="AI engineer building reliable agent systems.",
            evidence_ids=(evidence_id,),
        ),
        experience=(),
        projects=(
            ResumeEntry(
                element_id="projects.titan",
                heading="TITAN",
                subheading="Self-Correcting Resume Compiler",
                evidence_ids=(evidence_id,),
                bullets=(bullet,),
            ),
        ),
        skills=(
            EvidenceText(
                element_id="skills.languages",
                text="Languages: Python",
                evidence_ids=(evidence_id,),
            ),
        ),
        education=(),
        template_id="resume_v1",
        content_version=1,
    )


@pytest.mark.contract
def test_resume_content_accepts_strict_versioned_document() -> None:
    content = resume_content()

    assert content.template_id == "resume_v1"
    assert content.content_version == 1


@pytest.mark.contract
def test_resume_content_rejects_unknown_fields() -> None:
    payload = resume_content().model_dump()
    payload["raw_latex"] = r"\input{/etc/passwd}"

    with pytest.raises(ValidationError):
        ResumeContent.model_validate(payload)


@pytest.mark.contract
@pytest.mark.parametrize("content_version", [0, -1])
def test_resume_content_rejects_non_positive_version(content_version: int) -> None:
    payload = resume_content().model_dump()
    payload["content_version"] = content_version

    with pytest.raises(ValidationError):
        ResumeContent.model_validate(payload)


@pytest.mark.contract
def test_resume_content_rejects_unknown_nested_evidence_id() -> None:
    content = resume_content(evidence_id="project.unknown.001")

    with pytest.raises(UnknownEvidenceError, match=r"project\.unknown\.001"):
        validate_resume_content_evidence(content, (evidence("project.titan.001"),))


@pytest.mark.contract
def test_resume_content_accepts_known_nested_evidence_ids() -> None:
    evidence_record = evidence("project.titan.001")

    validate_resume_content_evidence(resume_content(), (evidence_record,))
