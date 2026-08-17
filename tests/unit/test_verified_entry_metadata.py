from datetime import date

import pytest

from app.models import EvidenceRecord, ResumeContent, ResumeEntry
from app.services.metadata import apply_verified_entry_metadata


@pytest.mark.unit
def test_verified_entry_metadata_replaces_model_structural_fields() -> None:
    record = EvidenceRecord(
        evidence_id="evidence.exp.example",
        source_type="experience",
        source_id="exp.example",
        claim="Example claim.",
        organization="Example Labs",
        title="AI Agent Intern",
        employment_type="internship",
        date_range="Jun 2025 - Aug 2025",
        location="Coimbatore",
        skills=("Python",),
        confidence=1.0,
        allowed_for_resume=True,
        last_verified_at=date(2026, 8, 12),
    )
    content = ResumeContent(
        resume_id="resume.metadata.001",
        target_role="AI Engineer",
        experience=(
            ResumeEntry(
                element_id="experience.example",
                heading="Invented Company",
                subheading="Invented Title",
                date_range="Invented Dates",
                location="Invented Location",
                evidence_ids=(record.evidence_id,),
            ),
        ),
    )

    enriched = apply_verified_entry_metadata(
        content=content, evidence_records=(record,)
    )

    entry = enriched.experience[0]
    assert entry.heading == "Example Labs"
    assert entry.subheading == "AI Agent Intern"
    assert entry.date_range == "Jun 2025 - Aug 2025"
    assert entry.location == "Coimbatore"
