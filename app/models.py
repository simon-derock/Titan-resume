"""Validated domain models for TITAN."""

from collections.abc import Iterable
from datetime import date
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Sha256Hex = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
ResumeTemplateId = Literal[
    "resume_v1",
    "moderncv_two_column_v1",
    "deedy_cv_v1",
]


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


class IngestedJobDescription(BaseModel):
    """Normalized, content-addressed job-description source text."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    raw_text: str = Field(min_length=1)
    raw_text_hash: Sha256Hex


class JobDescriptionAnalysisRequest(BaseModel):
    """Typed, content-addressed request passed to a JD analysis provider."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    raw_text: str = Field(min_length=1)
    raw_text_hash: Sha256Hex
    schema_version: Literal[1] = 1


class StructuredJobDescription(BaseModel):
    """Validated requirement groups extracted from one job description."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    role: str = Field(min_length=1)
    company: str = ""
    seniority: Literal[
        "intern",
        "entry",
        "mid",
        "senior",
        "lead",
        "principal",
        "unspecified",
    ] = "unspecified"
    must_have_skills: tuple[str, ...] = ()
    preferred_skills: tuple[str, ...] = ()
    responsibilities: tuple[str, ...] = ()
    domain: str = ""
    keywords: tuple[str, ...] = ()
    rejection_conditions: tuple[str, ...] = ()
    location_constraints: tuple[str, ...] = ()
    experience_requirements: tuple[str, ...] = ()
    raw_text_hash: Sha256Hex


class EvidenceMatch(BaseModel):
    """Deterministic support found for one structured JD skill requirement."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    requirement: str = Field(min_length=1)
    requirement_type: Literal["must_have", "preferred"]
    status: Literal["strong", "partial", "missing"]
    score: float = Field(ge=0.0, le=1.0)
    matched_components: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()


class SpacePlanningPolicy(BaseModel):
    """Reviewed physical limits for one locked resume template."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    total_line_limit: int = Field(default=47, ge=1)
    header_line_limit: int = Field(default=3, ge=2, le=3)
    summary_line_limit: int = Field(default=2, ge=0, le=2)
    experience_line_limit: int = Field(default=18, ge=16, le=20)
    project_line_limit: int = Field(default=18, ge=18, le=24)
    skills_line_limit: int = Field(default=4, ge=3, le=5)
    education_line_limit: int = Field(default=2, ge=1, le=2)
    experience_entry_limit: int = Field(default=3, ge=0, le=5)
    experience_bullets_per_entry_limit: int = Field(default=3, ge=0, le=3)
    project_entry_limit: int = Field(default=3, ge=0, le=6)
    project_bullets_per_entry_limit: int = Field(default=2, ge=0, le=2)
    education_entry_limit: int = Field(default=1, ge=0, le=1)

    @model_validator(mode="after")
    def validate_reserved_lines(self) -> Self:
        if self.reserved_line_count > self.total_line_limit:
            raise ValueError("reserved section lines exceed the total line limit")
        return self

    @property
    def reserved_line_count(self) -> int:
        return (
            self.header_line_limit
            + self.summary_line_limit
            + self.experience_line_limit
            + self.project_line_limit
            + self.skills_line_limit
            + self.education_line_limit
        )


class SectionSpaceBudget(BaseModel):
    """Line, entry, and bullet ceilings for one repeatable resume section."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    section: Literal["experience", "projects", "education"]
    line_limit: int = Field(ge=0)
    entry_limit: int = Field(ge=0)
    bullets_per_entry_limit: int = Field(ge=0)


class ResumeSpaceBudget(BaseModel):
    """Serializable section allocation for a single resume revision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    total_line_limit: int = Field(ge=1)
    header_line_limit: int = Field(ge=0)
    summary_line_limit: int = Field(ge=0)
    experience: SectionSpaceBudget
    projects: SectionSpaceBudget
    skills_line_limit: int = Field(ge=0)
    education: SectionSpaceBudget

    @property
    def reserved_line_count(self) -> int:
        return (
            self.header_line_limit
            + self.summary_line_limit
            + self.experience.line_limit
            + self.projects.line_limit
            + self.skills_line_limit
            + self.education.line_limit
        )


class ResumeStrategy(BaseModel):
    """Deterministic evidence selection and explicit requirement gaps."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    target_role: str = Field(min_length=1)
    selected_experience_evidence_ids: tuple[str, ...] = ()
    selected_project_evidence_ids: tuple[str, ...] = ()
    selected_skill_evidence_ids: tuple[str, ...] = ()
    selected_education_evidence_ids: tuple[str, ...] = ()
    omitted_evidence_ids: tuple[str, ...] = ()
    unmet_must_have_requirements: tuple[str, ...] = ()
    must_not_claim: tuple[str, ...] = ()


class ResumeWritingRequest(BaseModel):
    """Grounded, space-bounded input exposed to a resume writing provider."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    job_description: StructuredJobDescription
    strategy: ResumeStrategy
    space_budget: ResumeSpaceBudget
    selected_evidence: tuple[EvidenceRecord, ...]
    template_id: ResumeTemplateId = "resume_v1"
    repair_feedback: tuple[str, ...] = ()
    schema_version: Literal[1] = 1


class JobEvidenceIntelligenceResult(BaseModel):
    """Serializable output of the complete offline JD intelligence slice."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ingested_jd: IngestedJobDescription
    job_description: StructuredJobDescription
    evidence_matches: tuple[EvidenceMatch, ...]
    space_budget: ResumeSpaceBudget
    strategy: ResumeStrategy


class ResumeBullet(BaseModel):
    """One evidence-grounded, layout-budgeted resume statement."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    element_id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=205)
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


class GeometryPolicy(BaseModel):
    """Minimum safe whitespace around all rendered resume text."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    minimum_top_margin_pt: float = Field(default=18.0, ge=0.0)
    minimum_bottom_margin_pt: float = Field(default=20.0, ge=0.0)
    maximum_bottom_margin_pt: float = Field(default=60.0, ge=0.0)
    minimum_horizontal_margin_pt: float = Field(default=22.0, ge=0.0)
    maximum_column_bottom_delta_ratio: float = Field(
        default=0.16,
        ge=0.0,
        le=1.0,
    )

    @model_validator(mode="after")
    def validate_bottom_margin_range(self) -> Self:
        if self.maximum_bottom_margin_pt < self.minimum_bottom_margin_pt:
            raise ValueError(
                "maximum bottom margin must not be smaller than minimum bottom margin"
            )
        return self


class TextBox(BaseModel):
    """Measured page coordinates for one text-bearing element."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    element_id: str = Field(min_length=1)
    text: str
    x0: float
    y0: float
    x1: float
    y1: float


class PageGeometry(BaseModel):
    """Page dimensions and element-level text bounds in PDF points."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    width_pt: float = Field(gt=0.0)
    height_pt: float = Field(gt=0.0)
    text_boxes: tuple[TextBox, ...] = Field(min_length=1)


class GeometryReport(BaseModel):
    """Deterministic margin measurements and any resulting defects."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    passed: bool
    minimum_left_margin_pt: float
    minimum_right_margin_pt: float
    minimum_top_margin_pt: float
    minimum_bottom_margin_pt: float
    column_bottom_delta_pt: float | None = None
    issues: tuple[ValidationIssue, ...] = ()


class AtsValidationReport(BaseModel):
    """ATS text availability and logical reading-order result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    passed: bool
    text_extractable: bool
    reading_order_valid: bool
    issues: tuple[ValidationIssue, ...] = ()


class DeterministicPipelineResult(BaseModel):
    """Serializable artifacts and gate reports from the deterministic slice."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["passed", "compile_failed", "validation_failed"]
    passed: bool
    tex_path: str
    pdf_path: str | None = None
    screenshot_path: str | None = None
    compile_result: CompileResult
    page_report: PdfValidationReport | None = None
    ats_report: AtsValidationReport | None = None
    geometry_report: GeometryReport | None = None
    issues: tuple[ValidationIssue, ...] = ()


class BenchmarkEvaluationRecord(BaseModel):
    """Measured quality outcome for one fixed job-description benchmark."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    benchmark_id: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    role: str = Field(min_length=1)
    company: str = ""
    template_id: ResumeTemplateId
    status: Literal[
        "passed",
        "validation_failed",
        "compile_failed",
        "needs_review",
        "write_failed",
    ]
    passed: bool
    compile_success: bool
    exactly_one_page: bool
    ats_text_extractable: bool
    ats_reading_order_valid: bool
    geometry_passed: bool
    unsupported_claim_count: int = Field(ge=0)
    repair_iterations: int = Field(ge=0, le=3)
    elapsed_seconds: float = Field(ge=0.0)
    page_fill_percent: float | None = Field(default=None, ge=0.0, le=100.0)
    linked_entry_count: int = Field(default=0, ge=0)
    issue_types: tuple[str, ...] = ()


class BenchmarkJob(BaseModel):
    """One provenance-backed job description in the fixed evaluation corpus."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    benchmark_id: str = Field(min_length=1)
    platform: Literal["google_careers", "indeed", "linkedin", "wellfound"]
    source_url: str = Field(pattern=r"^https://")
    captured_at: date
    role: str = Field(min_length=1)
    company: str = Field(min_length=1)
    seniority: Literal[
        "intern",
        "entry",
        "mid",
        "senior",
        "lead",
        "principal",
        "unspecified",
    ]
    required_skills: tuple[str, ...] = Field(min_length=1)
    raw_text: str = Field(min_length=80)


class BenchmarkCorpus(BaseModel):
    """Versioned, immutable input set for repeatable resume evaluation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    captured_at: date
    description: str = Field(min_length=1)
    jobs: tuple[BenchmarkJob, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_benchmark_ids(self) -> Self:
        benchmark_ids = tuple(job.benchmark_id for job in self.jobs)
        if len(set(benchmark_ids)) != len(benchmark_ids):
            raise ValueError("benchmark IDs must be unique")
        return self


class EvaluationReport(BaseModel):
    """Deterministic aggregate metrics for one benchmark evaluation run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    benchmark_count: int = Field(ge=1)
    passed_count: int = Field(ge=0)
    pass_rate_percent: float = Field(ge=0.0, le=100.0)
    compile_success_rate_percent: float = Field(ge=0.0, le=100.0)
    exactly_one_page_rate_percent: float = Field(ge=0.0, le=100.0)
    ats_text_extraction_rate_percent: float = Field(ge=0.0, le=100.0)
    ats_reading_order_rate_percent: float = Field(ge=0.0, le=100.0)
    geometry_pass_rate_percent: float = Field(ge=0.0, le=100.0)
    unsupported_claim_rate_percent: float = Field(ge=0.0, le=100.0)
    average_repair_iterations: float = Field(ge=0.0)
    average_elapsed_seconds: float = Field(ge=0.0)
    average_page_fill_percent: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
    )
    records: tuple[BenchmarkEvaluationRecord, ...] = Field(min_length=1)


class ResumeEntry(BaseModel):
    """A role, project, or education entry containing grounded bullets."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    element_id: str = Field(min_length=1)
    heading: str = Field(min_length=1)
    subheading: str | None = None
    location: str | None = None
    date_range: str | None = None
    url: str | None = Field(default=None, pattern=r"^https://")
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
    template_id: ResumeTemplateId = "resume_v1"
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

    allowed_records = {
        record.evidence_id: record
        for record in evidence_records
        if record.allowed_for_resume
    }
    allowed_ids = set(allowed_records)
    unavailable_ids = sorted(referenced_ids - allowed_ids)
    if unavailable_ids:
        joined_ids = ", ".join(unavailable_ids)
        raise UnknownEvidenceError(f"unavailable evidence IDs: {joined_ids}")

    for entry in entries:
        if entry.url is None:
            continue
        verified_urls = {
            allowed_records[evidence_id].evidence_url
            for evidence_id in entry.evidence_ids
            if evidence_id in allowed_records
        }
        if entry.url not in verified_urls:
            raise UnknownEvidenceError(f"unverified entry URL: {entry.url}")


class ResumePolicy(BaseModel):
    """Hard document constraints that cannot be relaxed by repair logic."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    page_count: Literal[1] = 1
