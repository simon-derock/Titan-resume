import json
from dataclasses import dataclass, field
from pathlib import Path

from app.models import JobDescriptionAnalysisRequest
from app.services.intelligence import JobEvidenceIntelligencePipeline
from app.services.jd import JobDescriptionIngester, StructuredJobDescriptionAnalyzer
from app.services.profile import JsonCandidateEvidenceStore


@dataclass
class FakeStructuredJdClient:
    response: dict[str, object]
    requests: list[JobDescriptionAnalysisRequest] = field(default_factory=list)

    def analyze(self, request: JobDescriptionAnalysisRequest) -> object:
        self.requests.append(request)
        return self.response


def write_candidate_evidence(path: Path) -> None:
    records = [
        {
            "evidence_id": "evidence.experience.langgraph",
            "source_type": "experience",
            "source_id": "experience.blackcoat",
            "claim": "Built a grounded LangGraph agent workflow.",
            "skills": ["LangGraph"],
            "metrics": {},
            "evidence_url": None,
            "confidence": 1.0,
            "allowed_for_resume": True,
            "last_verified_at": "2026-08-04",
        },
        {
            "evidence_id": "evidence.experience.python",
            "source_type": "experience",
            "source_id": "experience.blackcoat",
            "claim": "Implemented the service in Python.",
            "skills": ["Python"],
            "metrics": {},
            "evidence_url": None,
            "confidence": 1.0,
            "allowed_for_resume": True,
            "last_verified_at": "2026-08-04",
        },
        {
            "evidence_id": "evidence.private.kubernetes",
            "source_type": "skill",
            "source_id": "skill.kubernetes",
            "claim": "Unreviewed Kubernetes claim.",
            "skills": ["Kubernetes"],
            "metrics": {},
            "evidence_url": None,
            "confidence": 0.5,
            "allowed_for_resume": False,
            "last_verified_at": "2026-08-04",
        },
        {
            "evidence_id": "evidence.project.fastapi",
            "source_type": "project",
            "source_id": "project.agent_api",
            "claim": "Served an agent workflow through FastAPI.",
            "skills": ["FastAPI"],
            "metrics": {},
            "evidence_url": None,
            "confidence": 1.0,
            "allowed_for_resume": True,
            "last_verified_at": "2026-08-04",
        },
    ]
    path.write_text(json.dumps(records), encoding="utf-8")


def test_golden_jd_intelligence_flow_preserves_grounding_and_rankings(
    tmp_path: Path,
) -> None:
    store_path = tmp_path / "evidence.json"
    write_candidate_evidence(store_path)
    client = FakeStructuredJdClient(
        response={
            "role": "AI Engineer",
            "company": "Example Labs",
            "seniority": "mid",
            "must_have_skills": ["LangGraph", "Python", "Kubernetes"],
            "preferred_skills": ["FastAPI"],
            "responsibilities": ["Build grounded agent services"],
            "domain": "Developer tooling",
            "keywords": ["agents", "RAG"],
            "rejection_conditions": [],
            "location_constraints": ["India"],
            "experience_requirements": ["Production Python experience"],
        }
    )
    pipeline = JobEvidenceIntelligencePipeline(
        ingester=JobDescriptionIngester(
            minimum_characters=40,
            maximum_characters=2_000,
        ),
        analyzer=StructuredJobDescriptionAnalyzer(client=client),
        evidence_store=JsonCandidateEvidenceStore(store_path),
    )

    result = pipeline.run(
        """
        Example Labs is hiring an AI Engineer to build reliable grounded agent
        services using LangGraph, Python, Kubernetes, and FastAPI. The engineer
        will own production evaluation and API delivery for developer tooling.
        """
    )

    assert result.job_description.raw_text_hash == result.ingested_jd.raw_text_hash
    assert tuple(
        (match.requirement, match.status, match.evidence_ids)
        for match in result.evidence_matches
    ) == (
        ("LangGraph", "strong", ("evidence.experience.langgraph",)),
        ("Python", "strong", ("evidence.experience.python",)),
        ("Kubernetes", "missing", ()),
        ("FastAPI", "strong", ("evidence.project.fastapi",)),
    )
    assert result.space_budget.experience.entry_limit == 1
    assert result.space_budget.projects.entry_limit == 1
    assert result.strategy.selected_experience_evidence_ids == (
        "evidence.experience.langgraph",
        "evidence.experience.python",
    )
    assert result.strategy.selected_project_evidence_ids == (
        "evidence.project.fastapi",
    )
    assert result.strategy.unmet_must_have_requirements == ("Kubernetes",)
    assert result.strategy.must_not_claim == ("Kubernetes",)
    assert "evidence.private.kubernetes" not in result.strategy.model_dump_json()
    assert len(client.requests) == 1
