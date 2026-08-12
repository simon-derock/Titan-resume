from datetime import date

import pytest

from app.models import (
    EvidenceRecord,
    EvidenceText,
    ResumeContent,
    StructuredJobDescription,
)
from app.services.skills import build_verified_skill_rail


def _record(
    evidence_id: str,
    *,
    skills: tuple[str, ...],
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        source_type="project",
        source_id=evidence_id,
        claim="Built a verified AI system.",
        skills=skills,
        confidence=1.0,
        allowed_for_resume=True,
        last_verified_at=date(2026, 8, 12),
    )


@pytest.mark.unit
def test_deedy_skill_rail_groups_only_verified_skills() -> None:
    engineering_id = "evidence.project.engineering"
    research_id = "evidence.project.research"
    content = ResumeContent(
        resume_id="resume.skill_rail.001",
        target_role="AI Engineer",
        skills=(
            EvidenceText(
                element_id="skills.generated",
                text="Generic AI skills",
                evidence_ids=(engineering_id,),
            ),
        ),
        template_id="deedy_cv_v1",
    )
    records = (
        _record(
            engineering_id,
            skills=("FastAPI", "Python", "LangGraph", "RAG"),
        ),
        _record(
            research_id,
            skills=("PyTorch", "QDoRA", "OpenCV"),
        ),
    )
    jd = StructuredJobDescription(
        role="AI Engineer",
        must_have_skills=("Python", "LangGraph"),
        raw_text_hash="a" * 64,
    )

    enriched = build_verified_skill_rail(
        content=content,
        evidence_records=records,
        job_description=jd,
    )

    element_ids = tuple(item.element_id for item in enriched.skills)
    assert "skills.engineering.heading" in element_ids
    assert "skills.agentic_ai.heading" in element_ids
    assert "skills.model_training_research.heading" in element_ids
    assert len(enriched.skills) > 6
    headings = tuple(
        item.text for item in enriched.skills if item.element_id.endswith(".heading")
    )
    assert headings == (
        "Engineering",
        "LLM & Agentic AI",
        "Model Training & Research",
    )
    tag_rows = tuple(
        item for item in enriched.skills if not item.element_id.endswith(".heading")
    )
    assert all(len(item.text) <= 28 for item in tag_rows)
    rendered = "\n".join(item.text for item in tag_rows)
    expected_skills = (
        "FastAPI",
        "Python",
        "LangGraph",
        "RAG",
        "PyTorch",
        "QDoRA",
        "OpenCV",
    )
    for skill in expected_skills:
        assert rendered.count(skill) == 1
    assert next(
        item for item in tag_rows if "FastAPI" in item.text
    ).evidence_ids == (engineering_id,)
    assert next(
        item for item in tag_rows if "PyTorch" in item.text
    ).evidence_ids == (research_id,)
    assert "Generic AI skills" not in rendered


@pytest.mark.unit
def test_skill_rail_leaves_non_deedy_templates_unchanged() -> None:
    evidence_id = "evidence.project.engineering"
    content = ResumeContent(
        resume_id="resume.skill_rail.single_column.001",
        target_role="AI Engineer",
        skills=(
            EvidenceText(
                element_id="skills.generated",
                text="Python, FastAPI",
                evidence_ids=(evidence_id,),
            ),
        ),
        template_id="resume_v1",
    )

    enriched = build_verified_skill_rail(
        content=content,
        evidence_records=(_record(evidence_id, skills=("Python", "FastAPI")),),
        job_description=StructuredJobDescription(
            role="AI Engineer",
            raw_text_hash="b" * 64,
        ),
    )

    assert enriched is content
