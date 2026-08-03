from datetime import date

import pytest
from pydantic import ValidationError

from app.models import (
    EvidenceRecord,
    ResumeBullet,
    UnknownEvidenceError,
    validate_evidence_references,
)


def allowed_evidence(evidence_id: str = "project.langgraph.001") -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        source_type="project",
        source_id="langgraph_agent",
        claim="Built a LangGraph workflow with bounded repair routing.",
        skills=("LangGraph", "Python"),
        confidence=1.0,
        allowed_for_resume=True,
        last_verified_at=date(2026, 8, 3),
    )


@pytest.mark.unit
def test_resume_bullet_requires_at_least_one_evidence_id() -> None:
    with pytest.raises(ValidationError):
        ResumeBullet(
            element_id="projects.langgraph_agent.bullet_1",
            text="Built a bounded repair workflow.",
            evidence_ids=(),
        )


@pytest.mark.unit
def test_resume_bullet_rejects_unknown_evidence_id() -> None:
    bullet = ResumeBullet(
        element_id="projects.langgraph_agent.bullet_1",
        text="Built a bounded repair workflow.",
        evidence_ids=("project.unknown.001",),
    )

    with pytest.raises(UnknownEvidenceError, match=r"project\.unknown\.001"):
        validate_evidence_references((bullet,), (allowed_evidence(),))


@pytest.mark.unit
def test_resume_bullet_accepts_allowed_existing_evidence_id() -> None:
    evidence = allowed_evidence()
    bullet = ResumeBullet(
        element_id="projects.langgraph_agent.bullet_1",
        text="Built a bounded repair workflow.",
        evidence_ids=(evidence.evidence_id,),
    )

    validate_evidence_references((bullet,), (evidence,))


@pytest.mark.unit
def test_resume_bullet_rejects_evidence_not_allowed_for_resume() -> None:
    evidence = allowed_evidence().model_copy(update={"allowed_for_resume": False})
    bullet = ResumeBullet(
        element_id="projects.langgraph_agent.bullet_1",
        text="Built a bounded repair workflow.",
        evidence_ids=(evidence.evidence_id,),
    )

    with pytest.raises(UnknownEvidenceError, match=evidence.evidence_id):
        validate_evidence_references((bullet,), (evidence,))
