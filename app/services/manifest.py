"""Deterministic resume inventory allocation before model writing."""

from collections import defaultdict

from app.models import (
    EvidenceMatch,
    EvidenceRecord,
    ResumeContentManifest,
    ResumeContentRequirements,
    StructuredJobDescription,
)


class ContentManifestError(ValueError):
    """Raised when requested resume inventory exceeds verified evidence."""


class ResumeContentManifestBuilder:
    """Allocate immutable resume slots from verified evidence and user counts."""

    def build(
        self,
        *,
        job_description: StructuredJobDescription,
        evidence_matches: tuple[EvidenceMatch, ...],
        evidence_records: tuple[EvidenceRecord, ...],
        requirements: ResumeContentRequirements,
    ) -> ResumeContentManifest:
        records = tuple(
            record for record in evidence_records if record.allowed_for_resume
        )
        experience_source_ids = _unique_source_ids(
            records,
            source_types={"experience", "internship"},
        )
        education_source_ids = _unique_source_ids(
            records,
            source_types={"education", "certification"},
        )
        project_records = tuple(
            record for record in records if record.source_type == "project"
        )
        project_source_ids = _ranked_source_ids(
            project_records,
            evidence_matches=evidence_matches,
        )
        if requirements.project_count > len(project_source_ids):
            raise ContentManifestError(
                f"requested {requirements.project_count} projects but only "
                f"{len(project_source_ids)} verified projects are available"
            )

        skill_names = _ranked_skill_names(
            records,
            job_description=job_description,
        )
        requested_skill_count = (
            len(skill_names)
            if requirements.skill_count is None
            else requirements.skill_count
        )
        if requested_skill_count > len(skill_names):
            raise ContentManifestError(
                f"requested {requested_skill_count} skills but only "
                f"{len(skill_names)} verified skills are available"
            )

        return ResumeContentManifest(
            experience_source_ids=experience_source_ids,
            project_source_ids=project_source_ids[: requirements.project_count],
            skill_names=skill_names[:requested_skill_count],
            education_source_ids=education_source_ids,
        )


def _unique_source_ids(
    records: tuple[EvidenceRecord, ...],
    *,
    source_types: set[str],
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            record.source_id for record in records if record.source_type in source_types
        )
    )


def _ranked_source_ids(
    records: tuple[EvidenceRecord, ...],
    *,
    evidence_matches: tuple[EvidenceMatch, ...],
) -> tuple[str, ...]:
    scores: defaultdict[str, float] = defaultdict(float)
    for match in evidence_matches:
        weight = 2.0 if match.requirement_type == "must_have" else 1.0
        for evidence_id in match.evidence_ids:
            scores[evidence_id] += weight * match.score

    records_by_source: dict[str, list[EvidenceRecord]] = {}
    for record in records:
        records_by_source.setdefault(record.source_id, []).append(record)
    source_order = {
        source_id: index for index, source_id in enumerate(records_by_source)
    }

    def source_rank(source_id: str) -> tuple[float, float, int]:
        source_records = records_by_source[source_id]
        return (
            -sum(scores[record.evidence_id] for record in source_records),
            -max(record.confidence for record in source_records),
            source_order[source_id],
        )

    return tuple(sorted(records_by_source, key=source_rank))


def _ranked_skill_names(
    records: tuple[EvidenceRecord, ...],
    *,
    job_description: StructuredJobDescription,
) -> tuple[str, ...]:
    skills_by_key: dict[str, str] = {}
    for record in records:
        for skill in record.skills:
            display = skill.strip()
            if display:
                skills_by_key.setdefault(display.casefold(), display)

    priority_terms = tuple(
        term.strip().casefold()
        for term in (
            *job_description.must_have_skills,
            *job_description.preferred_skills,
            *job_description.keywords,
        )
        if term.strip()
    )
    inventory_order = {key: index for index, key in enumerate(skills_by_key)}

    def skill_rank(key: str) -> tuple[int, int]:
        matching_priorities = tuple(
            index
            for index, term in enumerate(priority_terms)
            if key == term or key in term or term in key
        )
        return (
            min(matching_priorities, default=len(priority_terms)),
            inventory_order[key],
        )

    return tuple(skills_by_key[key] for key in sorted(skills_by_key, key=skill_rank))
