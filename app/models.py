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


class ResumePolicy(BaseModel):
    """Hard document constraints that cannot be relaxed by repair logic."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    page_count: Literal[1] = 1
