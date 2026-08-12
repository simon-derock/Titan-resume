from datetime import date

import pytest

from app.models import (
    EvidenceMatch,
    EvidenceRecord,
    ResumeContentRequirements,
    StructuredJobDescription,
)
from app.services.manifest import (
    ContentManifestError,
    ResumeContentManifestBuilder,
)


def _record(
    evidence_id: str,
    *,
    source_type: str,
    source_id: str,
    skills: tuple[str, ...],
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        source_type=source_type,
        source_id=source_id,
        claim=f"Verified claim for {source_id}.",
        skills=skills,
        confidence=1.0,
        allowed_for_resume=True,
        last_verified_at=date(2026, 8, 12),
    )


def _job() -> StructuredJobDescription:
    return StructuredJobDescription(
        role="AI Engineer",
        must_have_skills=("LangGraph", "Python"),
        preferred_skills=("FastAPI",),
        raw_text_hash="a" * 64,
    )


@pytest.mark.unit
def test_manifest_enforces_requested_inventory_counts() -> None:
    experiences = tuple(
        _record(
            f"evidence.exp.{index}",
            source_type="experience" if index < 4 else "internship",
            source_id=f"exp.{index}",
            skills=("Python", f"Experience Skill {index}"),
        )
        for index in range(5)
    )
    projects = tuple(
        _record(
            f"evidence.project.{index}",
            source_type="project",
            source_id=f"project.{index}",
            skills=(
                f"Project Skill {index}",
                *(("LangGraph",) if index == 7 else ()),
                *(("FastAPI",) if index == 3 else ()),
            ),
        )
        for index in range(10)
    )
    education = _record(
        "evidence.education.degree",
        source_type="education",
        source_id="education.degree",
        skills=("Artificial Intelligence",),
    )
    records = (*experiences, *projects, education)
    matches = (
        EvidenceMatch(
            requirement="LangGraph",
            requirement_type="must_have",
            status="strong",
            score=1.0,
            evidence_ids=(projects[7].evidence_id,),
        ),
        EvidenceMatch(
            requirement="FastAPI",
            requirement_type="preferred",
            status="strong",
            score=1.0,
            evidence_ids=(projects[3].evidence_id,),
        ),
    )

    manifest = ResumeContentManifestBuilder().build(
        job_description=_job(),
        evidence_matches=matches,
        evidence_records=records,
        requirements=ResumeContentRequirements(
            project_count=5,
            skill_count=10,
        ),
    )

    assert manifest.experience_source_ids == tuple(
        record.source_id for record in experiences
    )
    assert len(manifest.project_source_ids) == 5
    assert manifest.project_source_ids[:2] == ("project.7", "project.3")
    assert len(manifest.skill_names) == 10
    assert manifest.skill_names[:3] == ("LangGraph", "Python", "FastAPI")
    assert manifest.education_source_ids == (education.source_id,)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("requirements", "message"),
    [
        (
            ResumeContentRequirements(project_count=2),
            "requested 2 projects but only 1 verified projects are available",
        ),
        (
            ResumeContentRequirements(project_count=1, skill_count=4),
            "requested 4 skills but only 3 verified skills are available",
        ),
    ],
)
def test_manifest_rejects_counts_beyond_verified_inventory(
    requirements: ResumeContentRequirements,
    message: str,
) -> None:
    records = (
        _record(
            "evidence.exp.one",
            source_type="experience",
            source_id="exp.one",
            skills=("Python",),
        ),
        _record(
            "evidence.project.one",
            source_type="project",
            source_id="project.one",
            skills=("FastAPI", "LangGraph"),
        ),
    )

    with pytest.raises(ContentManifestError, match=f"^{message}$"):
        ResumeContentManifestBuilder().build(
            job_description=_job(),
            evidence_matches=(),
            evidence_records=records,
            requirements=requirements,
        )
