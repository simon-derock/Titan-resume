import copy
from dataclasses import dataclass, field
from datetime import date

import pytest

from app.models import (
    EvidenceRecord,
    ResumeSpaceBudget,
    ResumeStrategy,
    ResumeWritingRequest,
    SpacePlanningPolicy,
    StructuredJobDescription,
)
from app.services.planning import SpacePlanner
from app.services.writing import (
    ResumeWritingError,
    ResumeWritingInputError,
    StructuredResumeWriter,
)


@dataclass
class FakeResumeWriterClient:
    responses: list[object]
    requests: list[ResumeWritingRequest] = field(default_factory=list)

    def write(self, request: ResumeWritingRequest) -> object:
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def evidence(
    evidence_id: str,
    *,
    source_type: str,
    source_id: str,
    claim: str,
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        source_type=source_type,
        source_id=source_id,
        claim=claim,
        skills=("Python",),
        confidence=1.0,
        allowed_for_resume=True,
        last_verified_at=date(2026, 8, 4),
    )


def evidence_records() -> tuple[EvidenceRecord, ...]:
    return (
        evidence(
            "evidence.experience.agent",
            source_type="experience",
            source_id="experience.blackcoat",
            claim="Built a grounded LangGraph agent workflow.",
        ),
        evidence(
            "evidence.experience.api",
            source_type="experience",
            source_id="experience.blackcoat",
            claim="Served the workflow through FastAPI.",
        ),
        evidence(
            "evidence.project.evaluation",
            source_type="project",
            source_id="project.titan",
            claim="Created deterministic evaluation gates.",
        ),
        evidence(
            "evidence.skill.python",
            source_type="skill",
            source_id="skill.python",
            claim="Uses Python for production AI systems.",
        ),
        evidence(
            "evidence.education.degree",
            source_type="education",
            source_id="education.degree",
            claim="Completed a B.Tech in AI and Data Science.",
        ),
        evidence(
            "evidence.omitted.private",
            source_type="project",
            source_id="project.omitted",
            claim="This valid record was not selected by strategy.",
        ),
    )


def strategy() -> ResumeStrategy:
    return ResumeStrategy(
        target_role="AI Engineer",
        selected_experience_evidence_ids=(
            "evidence.experience.agent",
            "evidence.experience.api",
        ),
        selected_project_evidence_ids=("evidence.project.evaluation",),
        selected_skill_evidence_ids=("evidence.skill.python",),
        selected_education_evidence_ids=("evidence.education.degree",),
        omitted_evidence_ids=("evidence.omitted.private",),
        unmet_must_have_requirements=("Kubernetes",),
        must_not_claim=("Kubernetes",),
    )


def job_description() -> StructuredJobDescription:
    return StructuredJobDescription(
        role="AI Engineer",
        must_have_skills=("Python", "Kubernetes"),
        raw_text_hash="a" * 64,
    )


def space_budget() -> ResumeSpaceBudget:
    return SpacePlanner().plan(
        available_experience_entries=1,
        available_project_entries=1,
        available_education_entries=1,
    )


def valid_response() -> dict[str, object]:
    return {
        "resume_id": "resume.example.ai_engineer.001",
        "target_role": "AI Engineer",
        "summary": {
            "element_id": "summary.main",
            "text": "AI Engineer building grounded production agent systems.",
            "evidence_ids": ["evidence.experience.agent"],
        },
        "experience": [
            {
                "element_id": "experience.blackcoat",
                "heading": "Blackcoat AI",
                "subheading": "AI Engineer",
                "date_range": "2025-2026",
                "evidence_ids": [
                    "evidence.experience.agent",
                    "evidence.experience.api",
                ],
                "bullets": [
                    {
                        "element_id": "experience.blackcoat.agent",
                        "text": "Built a grounded LangGraph agent workflow.",
                        "evidence_ids": ["evidence.experience.agent"],
                        "priority": 1.0,
                        "target_max_lines": 2,
                        "protected_terms": ["LangGraph"],
                    },
                    {
                        "element_id": "experience.blackcoat.api",
                        "text": "Served agent capabilities through FastAPI.",
                        "evidence_ids": ["evidence.experience.api"],
                        "priority": 0.9,
                        "target_max_lines": 2,
                        "protected_terms": ["FastAPI"],
                    },
                ],
            }
        ],
        "projects": [
            {
                "element_id": "project.titan",
                "heading": "TITAN",
                "subheading": "Evidence-grounded resume compiler",
                "evidence_ids": ["evidence.project.evaluation"],
                "bullets": [
                    {
                        "element_id": "project.titan.evaluation",
                        "text": "Created deterministic evaluation gates.",
                        "evidence_ids": ["evidence.project.evaluation"],
                        "priority": 0.9,
                        "target_max_lines": 2,
                        "protected_terms": [],
                    }
                ],
            }
        ],
        "skills": [
            {
                "element_id": "skills.primary",
                "text": "Python",
                "evidence_ids": ["evidence.skill.python"],
            }
        ],
        "education": [
            {
                "element_id": "education.degree",
                "heading": "B.Tech in AI and Data Science",
                "evidence_ids": ["evidence.education.degree"],
                "bullets": [],
            }
        ],
        "template_id": "resume_v1",
        "content_version": 1,
    }


def writer(
    responses: list[object],
    *,
    max_attempts: int = 2,
) -> tuple[StructuredResumeWriter, FakeResumeWriterClient]:
    client = FakeResumeWriterClient(responses=responses)
    service = StructuredResumeWriter(client=client, max_attempts=max_attempts)
    return service, client


def write_resume(
    service: StructuredResumeWriter,
    *,
    records: tuple[EvidenceRecord, ...] | None = None,
    budget: ResumeSpaceBudget | None = None,
    template_id: str = "resume_v1",
):
    return service.write(
        job_description=job_description(),
        strategy=strategy(),
        space_budget=budget or space_budget(),
        evidence_records=records or evidence_records(),
        template_id=template_id,
    )


def test_writer_sends_only_strategy_selected_evidence() -> None:
    service, client = writer([valid_response()])

    result = write_resume(service)

    assert result.resume_id == "resume.example.ai_engineer.001"
    assert len(client.requests) == 1
    assert tuple(
        record.evidence_id for record in client.requests[0].selected_evidence
    ) == (
        "evidence.education.degree",
        "evidence.experience.agent",
        "evidence.experience.api",
        "evidence.project.evaluation",
        "evidence.skill.python",
    )
    assert "evidence.omitted.private" not in client.requests[0].model_dump_json()


def test_writer_enforces_the_requested_template() -> None:
    wrong_template = valid_response()
    requested_template = {
        **valid_response(),
        "template_id": "moderncv_two_column_v1",
    }
    service, client = writer([wrong_template, requested_template])

    result = write_resume(service, template_id="moderncv_two_column_v1")

    assert result.template_id == "moderncv_two_column_v1"
    assert len(client.requests) == 2
    assert client.requests[0].template_id == "moderncv_two_column_v1"


def test_writer_rejects_unavailable_selected_evidence_before_calling_client() -> None:
    records = tuple(
        record
        for record in evidence_records()
        if record.evidence_id != "evidence.experience.agent"
    )
    service, client = writer([valid_response()])

    with pytest.raises(
        ResumeWritingInputError,
        match=r"^unavailable selected evidence IDs: evidence\.experience\.agent$",
    ):
        write_resume(service, records=records)

    assert client.requests == []


def test_writer_retries_content_that_references_omitted_evidence() -> None:
    invalid = valid_response()
    invalid["summary"] = {
        "element_id": "summary.main",
        "text": "Unsupported omitted claim.",
        "evidence_ids": ["evidence.omitted.private"],
    }
    service, client = writer([invalid, valid_response()])

    result = write_resume(service)

    assert result.summary is not None
    assert result.summary.text.startswith("AI Engineer")
    assert len(client.requests) == 2


@pytest.mark.parametrize(
    "forbidden_text",
    [
        "Deployed Kubernetes clusters for production agents.",
        r"Built agents with \section{untrusted LaTeX}.",
    ],
)
def test_writer_rejects_forbidden_claims_and_raw_latex(forbidden_text: str) -> None:
    invalid = valid_response()
    invalid["summary"] = {
        "element_id": "summary.main",
        "text": forbidden_text,
        "evidence_ids": ["evidence.experience.agent"],
    }
    service, client = writer([invalid, valid_response()])

    result = write_resume(service)

    assert result.summary is not None
    assert result.summary.text != forbidden_text
    assert len(client.requests) == 2


def test_writer_rejects_content_outside_the_section_budget() -> None:
    invalid = valid_response()
    experience = invalid["experience"]
    assert isinstance(experience, list)
    first_entry = experience[0]
    assert isinstance(first_entry, dict)
    bullets = first_entry["bullets"]
    assert isinstance(bullets, list)
    first_entry["bullets"] = [*bullets, bullets[0], bullets[0]]
    service, client = writer([invalid, valid_response()])

    result = write_resume(service)

    assert len(result.experience[0].bullets) == 2
    assert len(client.requests) == 2


def test_writer_rejects_section_entry_overflow() -> None:
    invalid = valid_response()
    experience = invalid["experience"]
    assert isinstance(experience, list)
    experience.append(copy.deepcopy(experience[0]))
    service, client = writer([invalid, valid_response()])

    result = write_resume(service)

    assert len(result.experience) == 1
    assert len(client.requests) == 2


def test_writer_rejects_estimated_section_line_overflow() -> None:
    invalid = valid_response()
    experience = invalid["experience"]
    assert isinstance(experience, list)
    original_entry = experience[0]
    assert isinstance(original_entry, dict)
    expanded_entries = []
    for index in range(3):
        entry = copy.deepcopy(original_entry)
        entry["element_id"] = f"experience.blackcoat.{index}"
        bullets = entry["bullets"]
        assert isinstance(bullets, list)
        for bullet in bullets:
            assert isinstance(bullet, dict)
            bullet["target_max_lines"] = 3
        expanded_entries.append(entry)
    invalid["experience"] = expanded_entries
    expanded_budget = SpacePlanner().plan(
        available_experience_entries=3,
        available_project_entries=1,
        available_education_entries=1,
    )
    service, client = writer([invalid, valid_response()])

    result = write_resume(service, budget=expanded_budget)

    assert len(result.experience) == 1
    assert len(client.requests) == 2


def test_writer_rejects_skills_line_overflow() -> None:
    invalid = valid_response()
    skills = invalid["skills"]
    assert isinstance(skills, list)
    invalid["skills"] = [*skills, *skills, *skills, *skills, *skills]
    service, client = writer([invalid, valid_response()])

    result = write_resume(service)

    assert len(result.skills) == 1
    assert len(client.requests) == 2


def test_writer_rejects_summary_when_the_budget_disables_it() -> None:
    summary_free_budget = SpacePlanner(
        policy=SpacePlanningPolicy(summary_line_limit=0)
    ).plan(
        available_experience_entries=1,
        available_project_entries=1,
        available_education_entries=1,
    )
    service, client = writer([valid_response(), {**valid_response(), "summary": None}])

    result = write_resume(service, budget=summary_free_budget)

    assert result.summary is None
    assert len(client.requests) == 2


def test_writer_accepts_content_without_an_optional_summary() -> None:
    service, client = writer([{**valid_response(), "summary": None}])

    result = write_resume(service)

    assert result.summary is None
    assert len(client.requests) == 1


def test_writer_rejects_a_foreign_target_role() -> None:
    invalid = {**valid_response(), "target_role": "Kubernetes Engineer"}
    service, client = writer([invalid, valid_response()])

    result = write_resume(service)

    assert result.target_role == "AI Engineer"
    assert len(client.requests) == 2


def test_writer_retries_transient_client_failures() -> None:
    service, client = writer(
        [RuntimeError("temporary provider failure"), valid_response()]
    )

    result = write_resume(service)

    assert result.template_id == "resume_v1"
    assert len(client.requests) == 2


def test_writer_returns_a_sanitized_failure_after_retry_exhaustion() -> None:
    service, client = writer(
        [
            {"private_candidate_text": "confidential candidate evidence"},
            "unstructured confidential candidate evidence",
        ]
    )

    with pytest.raises(ResumeWritingError) as captured:
        write_resume(service)

    assert str(captured.value) == "structured resume writing failed after 2 attempts"
    assert captured.value.attempts == 2
    assert "confidential" not in str(captured.value)
    assert len(client.requests) == 2


@pytest.mark.parametrize("max_attempts", [0, 4])
def test_writer_rejects_an_unbounded_retry_policy(max_attempts: int) -> None:
    with pytest.raises(
        ValueError,
        match=r"^max_attempts must be between 1 and 3$",
    ):
        StructuredResumeWriter(
            client=FakeResumeWriterClient(responses=[]),
            max_attempts=max_attempts,
        )
