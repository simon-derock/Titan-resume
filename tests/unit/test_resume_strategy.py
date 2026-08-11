from datetime import date

import pytest

from app.models import (
    EvidenceMatch,
    EvidenceRecord,
    SpacePlanningPolicy,
    StructuredJobDescription,
)
from app.services.planning import SpacePlanner
from app.services.strategy import ResumeStrategyBuilder, StrategyPlanningError


def evidence(
    evidence_id: str,
    *,
    source_type: str = "experience",
    source_id: str,
    confidence: float = 1.0,
    allowed_for_resume: bool = True,
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        source_type=source_type,
        source_id=source_id,
        claim=f"Verified claim for {evidence_id}",
        skills=("Python",),
        confidence=confidence,
        allowed_for_resume=allowed_for_resume,
        last_verified_at=date(2026, 8, 4),
    )


def match(
    requirement: str,
    *,
    requirement_type: str,
    status: str = "strong",
    score: float = 1.0,
    evidence_ids: tuple[str, ...] = (),
) -> EvidenceMatch:
    return EvidenceMatch(
        requirement=requirement,
        requirement_type=requirement_type,
        status=status,
        score=score,
        evidence_ids=evidence_ids,
    )


def job() -> StructuredJobDescription:
    return StructuredJobDescription(
        role="AI Engineer",
        must_have_skills=("LangGraph", "Kubernetes"),
        preferred_skills=("Python",),
        raw_text_hash="0" * 64,
    )


def test_strategy_prioritizes_must_have_evidence_over_confidence() -> None:
    must_have = evidence(
        "evidence.must_have",
        source_id="experience.must_have",
        confidence=0.7,
    )
    preferred = evidence(
        "evidence.preferred",
        source_id="experience.preferred",
        confidence=1.0,
    )
    budget = SpacePlanner(policy=SpacePlanningPolicy(experience_entry_limit=1)).plan(
        available_experience_entries=2,
        available_project_entries=0,
        available_education_entries=0,
    )

    strategy = ResumeStrategyBuilder().build(
        job_description=job(),
        evidence_matches=(
            match(
                "LangGraph",
                requirement_type="must_have",
                evidence_ids=(must_have.evidence_id,),
            ),
            match(
                "Python",
                requirement_type="preferred",
                evidence_ids=(preferred.evidence_id,),
            ),
        ),
        evidence_records=(preferred, must_have),
        space_budget=budget,
    )

    assert strategy.selected_experience_evidence_ids == (must_have.evidence_id,)
    assert strategy.omitted_evidence_ids == (preferred.evidence_id,)


def test_strategy_applies_source_and_bullet_caps_deterministically() -> None:
    experience_records = tuple(
        evidence(
            f"evidence.experience.{source_index}.{bullet_index}",
            source_id=f"experience.{source_index}",
        )
        for source_index in range(1, 5)
        for bullet_index in range(1, 5)
    )
    project_records = tuple(
        evidence(
            f"evidence.project.{source_index}.{bullet_index}",
            source_type="project",
            source_id=f"project.{source_index}",
        )
        for source_index in range(1, 5)
        for bullet_index in range(1, 4)
    )
    records = (*experience_records, *project_records)
    budget = SpacePlanner().plan(
        available_experience_entries=4,
        available_project_entries=4,
        available_education_entries=0,
    )

    strategy = ResumeStrategyBuilder().build(
        job_description=job(),
        evidence_matches=(
            match(
                "Python",
                requirement_type="preferred",
                evidence_ids=tuple(record.evidence_id for record in records),
            ),
        ),
        evidence_records=records,
        space_budget=budget,
    )

    assert strategy.selected_experience_evidence_ids == tuple(
        f"evidence.experience.{source_index}.{bullet_index}"
        for source_index in range(1, 4)
        for bullet_index in range(1, 4)
    )
    assert strategy.selected_project_evidence_ids == tuple(
        f"evidence.project.{source_index}.{bullet_index}"
        for source_index in range(1, 4)
        for bullet_index in range(1, 3)
    )


def test_strategy_rejects_unknown_or_disallowed_match_references() -> None:
    private_record = evidence(
        "evidence.private",
        source_id="experience.private",
        allowed_for_resume=False,
    )
    budget = SpacePlanner().plan(
        available_experience_entries=0,
        available_project_entries=0,
        available_education_entries=0,
    )

    with pytest.raises(
        StrategyPlanningError,
        match=(
            r"^unavailable strategy evidence IDs: "
            r"evidence\.private, evidence\.unknown$"
        ),
    ):
        ResumeStrategyBuilder().build(
            job_description=job(),
            evidence_matches=(
                match(
                    "LangGraph",
                    requirement_type="must_have",
                    evidence_ids=("evidence.unknown", private_record.evidence_id),
                ),
            ),
            evidence_records=(private_record,),
            space_budget=budget,
        )


def test_strategy_carries_partial_and_missing_must_haves_as_gaps() -> None:
    budget = SpacePlanner().plan(
        available_experience_entries=0,
        available_project_entries=0,
        available_education_entries=0,
    )

    strategy = ResumeStrategyBuilder().build(
        job_description=job(),
        evidence_matches=(
            match(
                "LangGraph",
                requirement_type="must_have",
                status="partial",
                score=0.5,
            ),
            match(
                "Kubernetes",
                requirement_type="must_have",
                status="missing",
                score=0.0,
            ),
            match("Python", requirement_type="preferred", status="missing"),
        ),
        evidence_records=(),
        space_budget=budget,
    )

    assert strategy.unmet_must_have_requirements == ("LangGraph", "Kubernetes")
    assert strategy.must_not_claim == ("LangGraph", "Kubernetes")


def test_strategy_maps_skill_and_education_evidence_to_their_sections() -> None:
    skill_record = evidence(
        "evidence.skill.python",
        source_type="skill",
        source_id="skill.python",
    )
    education_record = evidence(
        "evidence.education.degree",
        source_type="education",
        source_id="education.degree",
    )
    budget = SpacePlanner().plan(
        available_experience_entries=0,
        available_project_entries=0,
        available_education_entries=1,
    )

    strategy = ResumeStrategyBuilder().build(
        job_description=job(),
        evidence_matches=(
            match(
                "Python",
                requirement_type="preferred",
                evidence_ids=(skill_record.evidence_id, education_record.evidence_id),
            ),
        ),
        evidence_records=(education_record, skill_record),
        space_budget=budget,
    )

    assert strategy.selected_skill_evidence_ids == (skill_record.evidence_id,)
    assert strategy.selected_education_evidence_ids == (education_record.evidence_id,)


def test_strategy_fills_open_template_capacity_after_relevance_ranking() -> None:
    """Unmatched verified history fills remaining space without outranking matches."""
    matched_experience = evidence(
        "evidence.experience.matched",
        source_id="experience.matched",
    )
    unmatched_experience = evidence(
        "evidence.experience.unmatched",
        source_id="experience.unmatched",
    )
    matched_project = evidence(
        "evidence.project.matched",
        source_type="project",
        source_id="project.matched",
    )
    unmatched_project = evidence(
        "evidence.project.unmatched",
        source_type="project",
        source_id="project.unmatched",
    )
    education_record = evidence(
        "evidence.education.degree",
        source_type="education",
        source_id="education.degree",
    )
    records = (
        unmatched_experience,
        unmatched_project,
        education_record,
        matched_experience,
        matched_project,
    )
    budget = SpacePlanner(
        policy=SpacePlanningPolicy(
            experience_entry_limit=2,
            project_entry_limit=2,
        )
    ).plan(
        available_experience_entries=2,
        available_project_entries=2,
        available_education_entries=1,
    )

    strategy = ResumeStrategyBuilder().build(
        job_description=job(),
        evidence_matches=(
            match(
                "LangGraph",
                requirement_type="must_have",
                evidence_ids=(matched_experience.evidence_id,),
            ),
            match(
                "Python",
                requirement_type="preferred",
                evidence_ids=(matched_project.evidence_id,),
            ),
        ),
        evidence_records=records,
        space_budget=budget,
    )

    assert strategy.selected_experience_evidence_ids == (
        matched_experience.evidence_id,
        unmatched_experience.evidence_id,
    )
    assert strategy.selected_project_evidence_ids == (
        matched_project.evidence_id,
        unmatched_project.evidence_id,
    )
    assert strategy.selected_education_evidence_ids == (education_record.evidence_id,)
    assert strategy.omitted_evidence_ids == ()
