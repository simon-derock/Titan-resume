from datetime import date

import pytest

from app.models import EvidenceRecord


@pytest.mark.unit
def test_evidence_record_preserves_structural_resume_fields() -> None:
    record = EvidenceRecord(
        evidence_id="evidence.exp.example",
        source_type="internship",
        source_id="exp.example",
        claim="Built an AI workflow.",
        organization="Example Labs",
        title="AI Agent Intern",
        employment_type="internship",
        date_range="Jun 2025 - Aug 2025",
        location="Coimbatore",
        description="Built and shipped a verified AI workflow.",
        skills=("Python",),
        confidence=1.0,
        allowed_for_resume=True,
        last_verified_at=date(2026, 8, 12),
    )

    assert record.organization == "Example Labs"
    assert record.title == "AI Agent Intern"
    assert record.employment_type == "internship"
    assert record.date_range == "Jun 2025 - Aug 2025"
    assert record.location == "Coimbatore"
    assert record.description == "Built and shipped a verified AI workflow."
