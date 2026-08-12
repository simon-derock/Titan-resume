"""Apply immutable evidence metadata to model-written resume entries."""

from collections.abc import Iterable

from app.models import EvidenceRecord, ResumeContent, ResumeEntry


def apply_verified_entry_metadata(
    *,
    content: ResumeContent,
    evidence_records: Iterable[EvidenceRecord],
) -> ResumeContent:
    records = {
        record.evidence_id: record
        for record in evidence_records
        if record.allowed_for_resume
    }

    def update_entries(entries: tuple[ResumeEntry, ...]) -> tuple[ResumeEntry, ...]:
        updated: list[ResumeEntry] = []
        for entry in entries:
            record = next(
                (
                    records[evidence_id]
                    for evidence_id in entry.evidence_ids
                    if evidence_id in records
                ),
                None,
            )
            if record is None:
                updated.append(entry)
                continue
            heading = record.organization or record.title or entry.heading
            subheading = entry.subheading
            if record.source_type in {"experience", "internship"}:
                subheading = record.title or subheading
            elif record.source_type == "education":
                heading = record.organization or heading
                subheading = record.title or subheading
            updated.append(
                entry.model_copy(
                    update={
                        "heading": heading,
                        "subheading": subheading,
                        "date_range": record.date_range or entry.date_range,
                        "location": record.location or entry.location,
                        "url": record.evidence_url or entry.url,
                    }
                )
            )
        return tuple(updated)

    return content.model_copy(
        update={
            "experience": update_entries(content.experience),
            "projects": update_entries(content.projects),
            "education": update_entries(content.education),
        }
    )
