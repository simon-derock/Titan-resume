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
    ) -> ResumeContent:
        """Return validated structured content or one sanitized typed failure."""

        allowed_records = {
            record.evidence_id: record
            for record in evidence_records
            if record.allowed_for_resume
        }
        selected_ids = _selected_evidence_ids(strategy)
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
                )
                return content
            except (
                ValidationError,
                UnknownEvidenceError,
                _ResumeWritingPolicyError,
            ):
                continue

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
) -> None:
    if content.target_role != strategy.target_role:
        raise _ResumeWritingPolicyError

    validate_resume_content_evidence(content, selected_evidence)
    rendered_text = "\n".join(_content_text(content))
    if any(
        _contains_protected_term(rendered_text, term)
        for term in strategy.must_not_claim
    ):
        raise _ResumeWritingPolicyError
    if re.search(r"\\[A-Za-z@]+", rendered_text):
        raise _ResumeWritingPolicyError

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
        raise _ResumeWritingPolicyError
    if content.summary is not None and space_budget.summary_line_limit == 0:
        raise _ResumeWritingPolicyError


def _validate_section_budget(
    entries: tuple[ResumeEntry, ...],
    *,
    entry_limit: int,
    bullets_per_entry_limit: int,
    line_limit: int,
) -> None:
    if len(entries) > entry_limit:
        raise _ResumeWritingPolicyError
    if any(len(entry.bullets) > bullets_per_entry_limit for entry in entries):
        raise _ResumeWritingPolicyError

    estimated_lines = sum(
        2 + sum(bullet.target_max_lines for bullet in entry.bullets)
        for entry in entries
    )
    if estimated_lines > line_limit:
        raise _ResumeWritingPolicyError


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
