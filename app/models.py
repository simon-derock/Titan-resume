"""Validated domain models for TITAN."""

from collections.abc import Iterable
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UnknownEvidenceError(ValueError):
    """Raised when resume content references unavailable candidate evidence."""


class EvidenceRecord(BaseModel):
    """A verified candidate claim that may be referenced by resume content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str = Field(min_length=1)
    source_type: Literal[
        "experience",
        "internship",
        "project",
        "skill",
        "achievement",
        "education",
        "certification",
    ]
    source_id: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    skills: tuple[str, ...] = ()
    metrics: dict[str, int | float] = Field(default_factory=dict)
    evidence_url: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    allowed_for_resume: bool
    last_verified_at: date


class ResumeBullet(BaseModel):
    """One evidence-grounded, layout-budgeted resume statement."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    element_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    priority: float = Field(default=0.0, ge=0.0, le=1.0)
    target_max_lines: int = Field(default=3, ge=1, le=3)
    protected_terms: tuple[str, ...] = ()


class EvidenceText(BaseModel):
    """A standalone piece of resume text with explicit provenance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    element_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(min_length=1)


class ResumeHeader(BaseModel):
    """Stable candidate identity and contact data rendered in the page header."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    headline: str = Field(min_length=1)
    location: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None


class CompileResult(BaseModel):
    """Serializable outcome from the restricted LaTeX subprocess."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    success: bool
    exit_code: int | None
    pdf_path: str | None
    log: str
    timed_out: bool = False
    error_type: (
        Literal["compilation_error", "timeout", "compiler_unavailable"] | None
    ) = None


class ValidationIssue(BaseModel):
    """One deterministic or advisory defect tied to a resume element."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    issue_id: str = Field(min_length=1)
    source: Literal["geometry", "vision", "ats", "provenance", "compiler"]
    element_id: str = ""
    issue_type: str = Field(min_length=1)
    severity: Literal["low", "medium", "high", "fatal"]
    message: str = Field(min_length=1)
    recommended_action: str = ""
    measured_value: int | float | str | None = None
    expected_value: int | float | str | None = None


class PdfValidationReport(BaseModel):
    """Typed deterministic validation result for a compiled PDF artifact."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    passed: bool
    page_count: int | None
    issues: tuple[ValidationIssue, ...] = ()


class ResumeEntry(BaseModel):
    """A role, project, or education entry containing grounded bullets."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    element_id: str = Field(min_length=1)
    heading: str = Field(min_length=1)
    subheading: str | None = None
    location: str | None = None
    date_range: str | None = None
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    bullets: tuple[ResumeBullet, ...] = ()


class ResumeContent(BaseModel):
    """Strict, renderer-independent content for one resume revision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    resume_id: str = Field(min_length=1)
    target_role: str = Field(min_length=1)
    summary: EvidenceText | None = None
    experience: tuple[ResumeEntry, ...] = ()
    projects: tuple[ResumeEntry, ...] = ()
    skills: tuple[EvidenceText, ...] = ()
    education: tuple[ResumeEntry, ...] = ()
    template_id: Literal["resume_v1"] = "resume_v1"
    content_version: int = Field(default=1, ge=1)


def validate_evidence_references(
    bullets: Iterable[ResumeBullet], evidence_records: Iterable[EvidenceRecord]
) -> None:
    """Reject bullet references that are unknown or not resume-allowlisted."""

    allowed_ids = {
        record.evidence_id for record in evidence_records if record.allowed_for_resume
    }
    unavailable_ids = sorted(
        {
            evidence_id
            for bullet in bullets
            for evidence_id in bullet.evidence_ids
            if evidence_id not in allowed_ids
        }
    )
    if unavailable_ids:
        joined_ids = ", ".join(unavailable_ids)
        raise UnknownEvidenceError(f"unavailable evidence IDs: {joined_ids}")


def validate_resume_content_evidence(
    content: ResumeContent, evidence_records: Iterable[EvidenceRecord]
) -> None:
    """Reject any unavailable evidence reference nested in resume content."""

    referenced_ids: set[str] = set()
    if content.summary is not None:
        referenced_ids.update(content.summary.evidence_ids)

    entries = (*content.experience, *content.projects, *content.education)
    for entry in entries:
        referenced_ids.update(entry.evidence_ids)
        for bullet in entry.bullets:
            referenced_ids.update(bullet.evidence_ids)

    for skill_line in content.skills:
        referenced_ids.update(skill_line.evidence_ids)

    allowed_ids = {
        record.evidence_id for record in evidence_records if record.allowed_for_resume
    }
    unavailable_ids = sorted(referenced_ids - allowed_ids)
    if unavailable_ids:
        joined_ids = ", ".join(unavailable_ids)
        raise UnknownEvidenceError(f"unavailable evidence IDs: {joined_ids}")


class ResumePolicy(BaseModel):
    """Hard document constraints that cannot be relaxed by repair logic."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    page_count: Literal[1] = 1
