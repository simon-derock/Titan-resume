"""Validated structured resume writing behind a replaceable client boundary."""

import re
from typing import Protocol

from pydantic import ValidationError

from app.models import (
    EvidenceRecord,
    ResumeContent,
    ResumeEntry,
    ResumeSpaceBudget,
    ResumeStrategy,
    ResumeTemplateId,
    ResumeWritingRequest,
    StructuredJobDescription,
    UnknownEvidenceError,
    validate_resume_content_evidence,
)


class ResumeWritingError(RuntimeError):
    """Raised after bounded structured-writing attempts are exhausted."""

    def __init__(self, *, attempts: int) -> None:
        self.attempts = attempts
        super().__init__(f"structured resume writing failed after {attempts} attempts")


class ResumeWritingInputError(ValueError):
    """Raised when grounded writer inputs are internally inconsistent."""


class StructuredResumeWriterClient(Protocol):
    """Replaceable provider boundary for structured resume content."""

    def write(self, request: ResumeWritingRequest) -> object: ...


class _ResumeWritingPolicyError(ValueError):
    """Internal signal for schema-valid content that violates writer policy."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class StructuredResumeWriter:
    """Accept only grounded, role-correct, line-budgeted resume content."""

    def __init__(
        self,
        *,
        client: StructuredResumeWriterClient,
        max_attempts: int = 2,
    ) -> None:
        if not 1 <= max_attempts <= 3:
            raise ValueError("max_attempts must be between 1 and 3")
        self._client = client
        self._max_attempts = max_attempts

    def write(
        self,
        *,
        job_description: StructuredJobDescription,
        strategy: ResumeStrategy,
        space_budget: ResumeSpaceBudget,
        evidence_records: tuple[EvidenceRecord, ...],
        template_id: ResumeTemplateId = "resume_v1",
    ) -> ResumeContent:
        """Return validated structured content or one sanitized typed failure."""

        allowed_records = {
            record.evidence_id: record
            for record in evidence_records
            if record.allowed_for_resume
        }
        selected_ids = _selected_evidence_ids(strategy)
        if not selected_ids:
            selected_ids = set(allowed_records.keys())

        unavailable_ids = sorted(selected_ids - allowed_records.keys())
        if unavailable_ids:
            joined_ids = ", ".join(unavailable_ids)
            raise ResumeWritingInputError(
                f"unavailable selected evidence IDs: {joined_ids}"
            )

        selected_evidence = tuple(
            allowed_records[evidence_id] for evidence_id in sorted(selected_ids)
        )

        provider_strategy = strategy.model_copy(update={"omitted_evidence_ids": ()})
        request = ResumeWritingRequest(
            job_description=job_description,
            strategy=provider_strategy,
            space_budget=space_budget,
            selected_evidence=selected_evidence,
            template_id=template_id,
        )
        for _ in range(self._max_attempts):
            try:
                response = self._client.write(request)
            except Exception:
                continue

            try:
                content = ResumeContent.model_validate(response)
                _validate_written_content(
                    content,
                    strategy=strategy,
                    space_budget=space_budget,
                    selected_evidence=selected_evidence,
                    template_id=template_id,
                )
                return content
            except ValidationError as exc:
                feedback = _schema_feedback(exc)
            except UnknownEvidenceError:
                feedback = ("evidence_provenance",)
            except _ResumeWritingPolicyError as exc:
                feedback = (exc.code,)

            request = request.model_copy(update={"repair_feedback": feedback})

        raise ResumeWritingError(attempts=self._max_attempts) from None


def _selected_evidence_ids(strategy: ResumeStrategy) -> set[str]:
    return {
        *strategy.selected_experience_evidence_ids,
        *strategy.selected_project_evidence_ids,
        *strategy.selected_skill_evidence_ids,
        *strategy.selected_education_evidence_ids,
    }


def _validate_written_content(
    content: ResumeContent,
    *,
    strategy: ResumeStrategy,
    space_budget: ResumeSpaceBudget,
    selected_evidence: tuple[EvidenceRecord, ...],
    template_id: ResumeTemplateId,
) -> None:
    if content.target_role != strategy.target_role:
        raise _ResumeWritingPolicyError("target_role")
    if content.template_id != template_id:
        raise _ResumeWritingPolicyError("template_id")

    validate_resume_content_evidence(content, selected_evidence)
    _validate_selected_section_evidence(content, selected_evidence)
    rendered_text = "\n".join(_content_text(content))
    if any(
        _contains_protected_term(rendered_text, term)
        for term in strategy.must_not_claim
    ):
        raise _ResumeWritingPolicyError("must_not_claim")
    if re.search(r"\\[A-Za-z@]+", rendered_text):
        raise _ResumeWritingPolicyError("raw_latex")

    _validate_section_budget(
        content.experience,
        entry_limit=space_budget.experience.entry_limit,
        bullets_per_entry_limit=(space_budget.experience.bullets_per_entry_limit),
        line_limit=space_budget.experience.line_limit,
    )
    _validate_section_budget(
        content.projects,
        entry_limit=space_budget.projects.entry_limit,
        bullets_per_entry_limit=space_budget.projects.bullets_per_entry_limit,
        line_limit=space_budget.projects.line_limit,
    )
    _validate_section_budget(
        content.education,
        entry_limit=space_budget.education.entry_limit,
        bullets_per_entry_limit=space_budget.education.bullets_per_entry_limit,
        line_limit=space_budget.education.line_limit,
    )
    if len(content.skills) > space_budget.skills_line_limit:
        raise _ResumeWritingPolicyError("skills_budget")
    if content.summary is not None and space_budget.summary_line_limit == 0:
        raise _ResumeWritingPolicyError("summary_budget")


def _validate_selected_section_evidence(
    content: ResumeContent,
    selected_evidence: tuple[EvidenceRecord, ...],
) -> None:
    section_specs = (
        (
            content.experience,
            {"experience", "internship"},
        ),
        (content.projects, {"project"}),
        (content.education, {"education", "certification"}),
    )
    records_by_id = {record.evidence_id: record for record in selected_evidence}

    for entries, source_types in section_specs:
        expected_records = tuple(
            record for record in selected_evidence if record.source_type in source_types
        )
        expected_ids = {record.evidence_id for record in expected_records}
        expected_sources = {record.source_id for record in expected_records}
        rendered_ids = {
            evidence_id
            for entry in entries
            for evidence_id in (
                *entry.evidence_ids,
                *(eid for bullet in entry.bullets for eid in bullet.evidence_ids),
            )
        }

        if not rendered_ids <= expected_ids or not expected_ids <= rendered_ids:
            raise _ResumeWritingPolicyError("selected_section_evidence")

        rendered_sources = {
            records_by_id[evidence_id].source_id for evidence_id in rendered_ids
        }
        if rendered_sources != expected_sources or len(entries) < len(expected_sources):
            raise _ResumeWritingPolicyError("selected_section_evidence")


def _validate_section_budget(
    entries: tuple[ResumeEntry, ...],
    *,
    entry_limit: int,
    bullets_per_entry_limit: int,
    line_limit: int,
) -> None:
    if len(entries) > entry_limit:
        raise _ResumeWritingPolicyError("section_entry_budget")
    if any(len(entry.bullets) > bullets_per_entry_limit for entry in entries):
        raise _ResumeWritingPolicyError("section_bullet_budget")

    estimated_lines = sum(
        2 + sum(bullet.target_max_lines for bullet in entry.bullets)
        for entry in entries
    )
    if estimated_lines > line_limit:
        raise _ResumeWritingPolicyError("section_line_budget")


def _schema_feedback(error: ValidationError) -> tuple[str, ...]:
    feedback = (
        "schema." + ".".join(str(part) for part in issue["loc"]) + f".{issue['type']}"
        for issue in error.errors(include_url=False, include_input=False)
    )
    return tuple(dict.fromkeys(feedback))


def _content_text(content: ResumeContent) -> tuple[str, ...]:
    text: list[str] = [content.target_role]
    if content.summary is not None:
        text.append(content.summary.text)
    for entry in (*content.experience, *content.projects, *content.education):
        text.extend(
            value
            for value in (
                entry.heading,
                entry.subheading,
                entry.location,
                entry.date_range,
            )
            if value is not None
        )
        text.extend(bullet.text for bullet in entry.bullets)
    text.extend(skill.text for skill in content.skills)
    return tuple(text)


def _contains_protected_term(text: str, term: str) -> bool:
    return (
        re.search(
            rf"(?<!\w){re.escape(term)}(?!\w)",
            text,
            flags=re.IGNORECASE,
        )
        is not None
    )
