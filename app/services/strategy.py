"""Grounded deterministic evidence selection for one resume revision."""

from collections import defaultdict

from app.models import (
    EvidenceMatch,
    EvidenceRecord,
    ResumeSpaceBudget,
    ResumeStrategy,
    StructuredJobDescription,
)


class StrategyPlanningError(ValueError):
    """Raised when strategy inputs violate evidence provenance."""


class ResumeStrategyBuilder:
    """Rank grounded evidence and fit it within section content ceilings."""

    def build(
        self,
        *,
        job_description: StructuredJobDescription,
        evidence_matches: tuple[EvidenceMatch, ...],
        evidence_records: tuple[EvidenceRecord, ...],
        space_budget: ResumeSpaceBudget,
    ) -> ResumeStrategy:
        """Build a stable, provenance-safe selection for downstream writing."""

        allowed_records = {
            record.evidence_id: record
            for record in evidence_records
            if record.allowed_for_resume
        }
        referenced_ids = {
            evidence_id
            for match in evidence_matches
            for evidence_id in match.evidence_ids
        }
        unavailable_ids = sorted(referenced_ids - allowed_records.keys())
        if unavailable_ids:
            joined_ids = ", ".join(unavailable_ids)
            raise StrategyPlanningError(
                f"unavailable strategy evidence IDs: {joined_ids}"
            )

        scores: defaultdict[str, float] = defaultdict(float)
        for match in evidence_matches:
            requirement_weight = 2.0 if match.requirement_type == "must_have" else 1.0
            for evidence_id in match.evidence_ids:
                scores[evidence_id] += requirement_weight * match.score

        candidate_records = tuple(allowed_records.values())
        selected_experience = _select_grouped_records(
            records=tuple(
                record
                for record in candidate_records
                if record.source_type in {"experience", "internship"}
            ),
            scores=scores,
            source_limit=space_budget.experience.entry_limit,
            records_per_source_limit=(space_budget.experience.bullets_per_entry_limit),
        )
        selected_projects = _select_grouped_records(
            records=tuple(
                record
                for record in candidate_records
                if record.source_type == "project"
            ),
            scores=scores,
            source_limit=space_budget.projects.entry_limit,
            records_per_source_limit=space_budget.projects.bullets_per_entry_limit,
        )
        selected_skills = tuple(
            sorted(
                (
                    record
                    for record in candidate_records
                    if record.source_type == "skill"
                ),
                key=lambda record: _record_rank(record, scores),
            )[: space_budget.skills_line_limit]
        )
        selected_education = _select_grouped_records(
            records=tuple(
                record
                for record in candidate_records
                if record.source_type in {"education", "certification"}
            ),
            scores=scores,
            source_limit=space_budget.education.entry_limit,
            records_per_source_limit=1,
        )

        selected_ids = {
            record.evidence_id
            for record in (
                *selected_experience,
                *selected_projects,
                *selected_skills,
                *selected_education,
            )
        }
        unmet_must_haves = tuple(
            dict.fromkeys(
                match.requirement
                for match in evidence_matches
                if match.requirement_type == "must_have" and match.status != "strong"
            )
        )
        return ResumeStrategy(
            target_role=job_description.role,
            selected_experience_evidence_ids=tuple(
                record.evidence_id for record in selected_experience
            ),
            selected_project_evidence_ids=tuple(
                record.evidence_id for record in selected_projects
            ),
            selected_skill_evidence_ids=tuple(
                record.evidence_id for record in selected_skills
            ),
            selected_education_evidence_ids=tuple(
                record.evidence_id for record in selected_education
            ),
            omitted_evidence_ids=tuple(sorted(allowed_records.keys() - selected_ids)),
            unmet_must_have_requirements=unmet_must_haves,
            must_not_claim=unmet_must_haves,
        )


def _select_grouped_records(
    *,
    records: tuple[EvidenceRecord, ...],
    scores: dict[str, float],
    source_limit: int,
    records_per_source_limit: int,
) -> tuple[EvidenceRecord, ...]:
    records_by_source: defaultdict[str, list[EvidenceRecord]] = defaultdict(list)
    for record in records:
        records_by_source[record.source_id].append(record)

    ranked_sources: list[tuple[tuple[float, float, str], str]] = []
    for source_id, source_records in records_by_source.items():
        source_records.sort(key=lambda record: _record_rank(record, scores))
        ranked_sources.append((_record_rank(source_records[0], scores), source_id))
    ranked_sources.sort(key=lambda source: (source[0], source[1]))

    selected: list[EvidenceRecord] = []
    for _, source_id in ranked_sources[:source_limit]:
        selected.extend(records_by_source[source_id][:records_per_source_limit])
    return tuple(selected)


def _record_rank(
    record: EvidenceRecord,
    scores: dict[str, float],
) -> tuple[float, float, str]:
    return (-scores[record.evidence_id], -record.confidence, record.evidence_id)
