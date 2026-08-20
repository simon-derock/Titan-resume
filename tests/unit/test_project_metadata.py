from datetime import date

import pytest

from app.models import (
    EvidenceRecord,
    ResumeContent,
    ResumeEntry,
    StructuredJobDescription,
)
from app.services.skills import build_verified_project_stacks


def _record(*, claim: str) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id="evidence.project.dex",
        source_type="project",
        source_id="project.dex",
        claim=claim,
        skills=(
            "Python",
            "Qdrant",
            "Jina Embeddings",
            "Cerebras",
            "Groq",
            "Mistral",
            "Telegram Bot API",
        ),
        evidence_url="https://github.com/example/dex",
        confidence=1.0,
        allowed_for_resume=True,
        last_verified_at=date(2026, 8, 12),
    )


@pytest.mark.unit
def test_deedy_project_stack_replaces_generic_unverified_metadata() -> None:
    evidence_id = "evidence.project.dex"
    content = ResumeContent(
        resume_id="resume.project_stack.001",
        target_role="AI Engineer",
        projects=(
            ResumeEntry(
                element_id="projects.dex",
                heading="DEX Jobs",
                subheading="Personal Project",
                date_range="2025",
                evidence_ids=(evidence_id,),
            ),
        ),
        template_id="deedy_cv_v1",
    )

    enriched = build_verified_project_stacks(
        content=content,
        evidence_records=(_record(claim="Built a grounded job agent."),),
        job_description=StructuredJobDescription(
            role="AI Engineer",
            must_have_skills=("Python", "Qdrant"),
            raw_text_hash="a" * 64,
        ),
    )

    project = enriched.projects[0]
    assert project.subheading == (
        "Python | Qdrant | Jina Embeddings | Cerebras | Groq | Mistral"
    )
    assert len(project.subheading) <= 72
    assert project.date_range is None


@pytest.mark.unit
def test_deedy_project_stack_preserves_evidence_supported_date() -> None:
    evidence_id = "evidence.project.dex"
    content = ResumeContent(
        resume_id="resume.project_stack.dated.001",
        target_role="AI Engineer",
        projects=(
            ResumeEntry(
                element_id="projects.dex",
                heading="DEX Jobs",
                date_range="2025",
                evidence_ids=(evidence_id,),
            ),
        ),
        template_id="deedy_cv_v1",
    )

    enriched = build_verified_project_stacks(
        content=content,
        evidence_records=(_record(claim="Shipped DEX Jobs in 2025."),),
        job_description=StructuredJobDescription(
            role="AI Engineer",
            raw_text_hash="b" * 64,
        ),
    )

    assert enriched.projects[0].date_range == "2025"


@pytest.mark.unit
def test_project_stack_enriches_single_column_templates_too() -> None:
    evidence_id = "evidence.project.dex"
    content = ResumeContent(
        resume_id="resume.project_stack.single_column.001",
        target_role="AI Engineer",
        projects=(
            ResumeEntry(
                element_id="projects.dex",
                heading="DEX Jobs",
                subheading="Personal Project",
                evidence_ids=(evidence_id,),
            ),
        ),
        template_id="resume_v1",
    )

    enriched = build_verified_project_stacks(
        content=content,
        evidence_records=(_record(claim="Built a grounded job agent."),),
        job_description=StructuredJobDescription(
            role="AI Engineer",
            raw_text_hash="c" * 64,
        ),
    )

    assert enriched is not content
    assert enriched.projects[0].subheading == (
        "Python | Qdrant | Jina Embeddings | Cerebras | Groq | Mistral"
    )
