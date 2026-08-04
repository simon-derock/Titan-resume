from datetime import date

from app.models import EvidenceRecord, StructuredJobDescription
from app.services.matching import EvidenceMatcher


def evidence(
    evidence_id: str,
    *,
    skills: tuple[str, ...],
    allowed_for_resume: bool = True,
    claim: str = "Built a production AI system.",
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        source_type="project",
        source_id="project.example",
        claim=claim,
        skills=skills,
        confidence=1.0,
        allowed_for_resume=allowed_for_resume,
        last_verified_at=date(2026, 8, 4),
    )


def job(
    *,
    must_have_skills: tuple[str, ...] = (),
    preferred_skills: tuple[str, ...] = (),
) -> StructuredJobDescription:
    return StructuredJobDescription(
        role="AI Engineer",
        must_have_skills=must_have_skills,
        preferred_skills=preferred_skills,
        raw_text_hash="0" * 64,
    )


def test_evidence_matcher_resolves_known_skill_aliases() -> None:
    matches = EvidenceMatcher().match(
        job_description=job(must_have_skills=("Retrieval-Augmented Generation",)),
        evidence_records=(evidence("evidence.rag", skills=("RAG",)),),
    )

    assert len(matches) == 1
    assert matches[0].status == "strong"
    assert matches[0].score == 1.0
    assert matches[0].matched_components == ("rag",)
    assert matches[0].evidence_ids == ("evidence.rag",)


def test_evidence_matcher_never_uses_disallowed_or_claim_only_skills() -> None:
    matches = EvidenceMatcher().match(
        job_description=job(must_have_skills=("Kubernetes", "Terraform")),
        evidence_records=(
            evidence(
                "evidence.private_kubernetes",
                skills=("Kubernetes",),
                allowed_for_resume=False,
            ),
            evidence(
                "evidence.claim_only_terraform",
                skills=("Python",),
                claim="Provisioned production infrastructure with Terraform.",
            ),
        ),
    )

    assert tuple(match.status for match in matches) == ("missing", "missing")
    assert all(match.evidence_ids == () for match in matches)


def test_evidence_matcher_reports_partial_compound_requirements() -> None:
    (match,) = EvidenceMatcher().match(
        job_description=job(must_have_skills=("Python and FastAPI",)),
        evidence_records=(evidence("evidence.python", skills=("Python",)),),
    )

    assert match.status == "partial"
    assert match.score == 0.5
    assert match.matched_components == ("python",)
    assert match.evidence_ids == ("evidence.python",)


def test_evidence_matcher_combines_records_for_a_compound_requirement() -> None:
    (match,) = EvidenceMatcher().match(
        job_description=job(must_have_skills=("Python / FastAPI",)),
        evidence_records=(
            evidence("evidence.python", skills=("Python",)),
            evidence("evidence.fastapi", skills=("FastAPI",)),
        ),
    )

    assert match.status == "strong"
    assert match.score == 1.0
    assert match.matched_components == ("python", "fastapi")
    assert match.evidence_ids == ("evidence.fastapi", "evidence.python")


def test_evidence_matcher_uses_stable_ids_to_break_equal_scores() -> None:
    (match,) = EvidenceMatcher().match(
        job_description=job(preferred_skills=("Python",)),
        evidence_records=(
            evidence("evidence.zulu", skills=("Python",)),
            evidence("evidence.alpha", skills=("Python",)),
        ),
    )

    assert match.requirement_type == "preferred"
    assert match.evidence_ids == ("evidence.alpha", "evidence.zulu")


def test_evidence_matcher_preserves_requirement_group_order() -> None:
    matches = EvidenceMatcher().match(
        job_description=job(
            must_have_skills=("Python", "LangGraph"),
            preferred_skills=("FastAPI",),
        ),
        evidence_records=(),
    )

    assert tuple((match.requirement_type, match.requirement) for match in matches) == (
        ("must_have", "Python"),
        ("must_have", "LangGraph"),
        ("preferred", "FastAPI"),
    )
