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


def evidence(
    evidence_id: str,
    *,
    evidence_url: str | None = None,
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        source_type="project",
        source_id="titan",
        claim="Built a deterministic resume compiler.",
        skills=("Python",),
        evidence_url=evidence_url,
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


@pytest.mark.contract
def test_resume_content_accepts_entry_url_verified_by_its_evidence() -> None:
    verified_url = "https://github.com/alex/titan"
    evidence_record = evidence(
        "project.titan.001",
        evidence_url=verified_url,
    )
    project = ResumeEntry(
        element_id="projects.titan",
        heading="TITAN",
        url=verified_url,
        evidence_ids=(evidence_record.evidence_id,),
    )
    content = resume_content().model_copy(update={"projects": (project,)})

    validate_resume_content_evidence(content, (evidence_record,))


@pytest.mark.contract
def test_resume_content_rejects_entry_url_not_verified_by_its_evidence() -> None:
    evidence_record = evidence(
        "project.titan.001",
        evidence_url="https://github.com/alex/titan",
    )
    project = ResumeEntry(
        element_id="projects.titan",
        heading="TITAN",
        url="https://example.com/invented",
        evidence_ids=(evidence_record.evidence_id,),
    )
    content = resume_content().model_copy(update={"projects": (project,)})

    with pytest.raises(UnknownEvidenceError, match="unverified entry URL"):
        validate_resume_content_evidence(content, (evidence_record,))


@pytest.mark.contract
def test_resume_entry_rejects_non_https_url() -> None:
    with pytest.raises(ValidationError):
        ResumeEntry(
            element_id="projects.titan",
            heading="TITAN",
            url="javascript:alert(1)",
            evidence_ids=("project.titan.001",),
        )


@pytest.mark.contract
def test_resume_bullet_rejects_text_beyond_dense_two_line_ceiling() -> None:
    with pytest.raises(ValidationError):
        ResumeBullet(
            element_id="projects.titan.bullet",
            text="x" * 161,
            evidence_ids=("project.titan.001",),
            target_max_lines=2,
        )
