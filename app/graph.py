"""Bounded resume generation and repair graph.

This module provides a pure-Python typed executor that wires the full
resume pipeline in a state-machine loop:

    write_resume → render+compile → validate
        ↓ pass              → done (status='passed')
        ↓ compile_failed    → halt (status='compile_failed')
        ↓ validation_failed → if budget: repair → render+compile → validate
                              else: halt (status='needs_review')
        ↓ write_failed      → halt (status='write_failed')

The loop is bounded by max_repair_cycles (default 2, hard max 3) and does
not require LangGraph.  When checkpoint/resume or Telegram HITL is needed,
this executor can be wrapped in a LangGraph StateGraph without changing any
node logic.

All collaborators (writer, pipeline) are injected so tests can supply stubs.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TypedDict

from app.models import (
    DeterministicPipelineResult,
    EvidenceRecord,
    IngestedJobDescription,
    ResumeContent,
    ResumeContentManifest,
    ResumeContentRequirements,
    ResumeHeader,
    ResumeSpaceBudget,
    ResumeStrategy,
    ResumeTemplateId,
    StructuredJobDescription,
    ValidationIssue,
)
from app.services.writing import ResumeWritingError, StructuredResumeWriter

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# State TypedDict
# ---------------------------------------------------------------------------


class ResumeGraphState(TypedDict, total=False):
    """Serialisable state object threaded through every graph step.

    Required keys (always present after run() begins):
        request_id, raw_jd_text, status, iteration, max_repair_cycles,
        pipeline_result, issues
    Optional keys (present when available):
        resume_content, repair_feedback
    """

    request_id: str
    raw_jd_text: str
    # 'running' | 'passed' | 'compile_failed' | 'needs_review' | 'write_failed'
    status: str
    iteration: int
    max_repair_cycles: int
    pipeline_result: DeterministicPipelineResult | None
    issues: tuple[ValidationIssue, ...]
    resume_content: ResumeContent | None
    repair_feedback: str | None


# ---------------------------------------------------------------------------
# Collaborator protocols (injectable for testing)
# ---------------------------------------------------------------------------


class _WriterClient(Protocol):
    """Minimal write() interface — satisfied by StructuredResumeWriterClient."""

    def write(self, request: object) -> object: ...


class _PipelineRunner(Protocol):
    """Minimal run() interface — satisfied by DeterministicResumePipeline."""

    def run(
        self,
        header: ResumeHeader,
        content: ResumeContent,
        evidence_records: Iterable[EvidenceRecord],
        output_directory: Path,
    ) -> DeterministicPipelineResult: ...


class _JdAnalyzer(Protocol):
    """Minimal typed boundary for structured job-description analysis."""

    def analyze(self, document: IngestedJobDescription) -> StructuredJobDescription: ...


# ---------------------------------------------------------------------------
# ResumeGraphExecutor
# ---------------------------------------------------------------------------

_MAX_REPAIR_CYCLES_HARD_CAP = 3


class ResumeGraphExecutor:
    """Bounded typed state-machine executor for the resume generation loop.

    Parameters
    ----------
    writer:
        Any object satisfying StructuredResumeWriterClient — typically a
        StructuredResumeWriter wrapping a PromptResumeWriterClient.
    pipeline:
        Any object satisfying _PipelineRunner — typically a
        DeterministicResumePipeline.
    max_repair_cycles:
        Maximum number of repair iterations after the first compile+validate
        attempt.  Must be between 1 and 3 (per project invariants).
    """

    def __init__(
        self,
        *,
        writer: _WriterClient | StructuredResumeWriter,
        pipeline: _PipelineRunner,
        jd_analyzer: _JdAnalyzer | None = None,
        max_repair_cycles: int = 2,
    ) -> None:
        if not 1 <= max_repair_cycles <= _MAX_REPAIR_CYCLES_HARD_CAP:
            raise ValueError(
                f"max_repair_cycles must be between 1 and {_MAX_REPAIR_CYCLES_HARD_CAP}"
            )
        self._writer = writer
        self._pipeline = pipeline
        self._jd_analyzer = jd_analyzer
        self.max_repair_cycles = max_repair_cycles

    def run(
        self,
        *,
        raw_jd_text: str,
        header: ResumeHeader,
        evidence_records: tuple[EvidenceRecord, ...],
        output_dir: Path,
        template_id: ResumeTemplateId = "resume_v1",
        request_id: str | None = None,
        requirements: ResumeContentRequirements | None = None,
    ) -> ResumeGraphState:
        """Execute the full generation loop and return the terminal state."""

        state: ResumeGraphState = {
            "request_id": request_id or str(uuid.uuid4()),
            "raw_jd_text": raw_jd_text,
            "status": "running",
            "iteration": 0,
            "max_repair_cycles": self.max_repair_cycles,
            "pipeline_result": None,
            "issues": (),
            "resume_content": None,
            "repair_feedback": None,
        }

        # ------------------------------------------------------------------ #
        # Step 1 — offline intelligence (deterministic, no LLM)
        # ------------------------------------------------------------------ #
        from app.services.jd import JobDescriptionIngester
        from app.services.manifest import (
            ContentManifestError,
            ResumeContentManifestBuilder,
        )
        from app.services.matching import EvidenceMatcher
        from app.services.planning import SpacePlanner
        from app.services.strategy import ResumeStrategyBuilder

        try:
            ingested_jd = JobDescriptionIngester().ingest(raw_jd_text)
        except Exception as exc:
            state["status"] = "write_failed"
            state["repair_feedback"] = f"JD ingestion failed: {exc}"
            return state

        if self._jd_analyzer is not None:
            try:
                jd = self._jd_analyzer.analyze(ingested_jd)
            except Exception as exc:
                state["status"] = "write_failed"
                state["repair_feedback"] = f"JD analysis failed: {exc}"
                return state
        else:
            # Deterministic fallback retained for offline callers and tests.
            first_line = ingested_jd.raw_text.splitlines()[0].strip()[:120]
            jd = StructuredJobDescription(
                role=first_line or "Engineer",
                raw_text_hash=ingested_jd.raw_text_hash,
            )

        evidence_matches = EvidenceMatcher().match(
            job_description=jd,
            evidence_records=evidence_records,
        )
        space_budget = SpacePlanner().plan(
            available_experience_entries=_source_count(
                evidence_records, source_types={"experience", "internship"}
            ),
            available_project_entries=_source_count(
                evidence_records, source_types={"project"}
            ),
            available_education_entries=_source_count(
                evidence_records, source_types={"education", "certification"}
            ),
            template_id=template_id,
        )
        if requirements is None:
            requirements = _default_content_requirements(
                template_id=template_id,
                available_projects=_source_count(
                    evidence_records, source_types={"project"}
                ),
                available_skills=_skill_inventory_count(evidence_records),
            )
        try:
            manifest = ResumeContentManifestBuilder().build(
                job_description=jd,
                evidence_matches=evidence_matches,
                evidence_records=evidence_records,
                requirements=requirements,
            )
            _validate_manifest_capacity(manifest, space_budget)
        except ContentManifestError as exc:
            state["status"] = "write_failed"
            state["repair_feedback"] = str(exc)
            return state
        except ValueError as exc:
            state["status"] = "write_failed"
            state["repair_feedback"] = f"content manifest infeasible: {exc}"
            return state
        strategy = ResumeStrategyBuilder().build(
            job_description=jd,
            evidence_matches=evidence_matches,
            evidence_records=evidence_records,
            space_budget=space_budget,
        )
        strategy = _apply_content_manifest(strategy, manifest, evidence_records)

        from app.models import ResumeWritingRequest

        # ------------------------------------------------------------------ #
        # Step 2 — write → compile → validate loop
        # ------------------------------------------------------------------ #
        max_total = self.max_repair_cycles + 1  # first attempt + repairs
        repair_feedback: tuple[str, ...] = ()

        for attempt in range(1, max_total + 1):
            state["iteration"] = attempt

            # Build request (include repair feedback when available)
            request = ResumeWritingRequest(
                job_description=jd,
                strategy=strategy.model_copy(update={"omitted_evidence_ids": ()}),
                space_budget=space_budget,
                selected_evidence=_selected_evidence(strategy, evidence_records),
                content_manifest=manifest,
                template_id=template_id,
                repair_feedback=repair_feedback,
            )

            # Write -------------------------------------------------------- #
            try:
                if isinstance(self._writer, StructuredResumeWriter):
                    content = self._writer.write(
                        job_description=jd,
                        strategy=strategy,
                        space_budget=space_budget,
                        evidence_records=evidence_records,
                        template_id=template_id,
                        repair_feedback=repair_feedback,
                        content_manifest=manifest,
                    )
                else:
                    raw = self._writer.write(request)
                    content = (
                        raw
                        if isinstance(raw, ResumeContent)
                        else ResumeContent.model_validate(raw)
                    )
            except ResumeWritingError as exc:
                state["status"] = "write_failed"
                state["repair_feedback"] = str(exc)
                return state
            except Exception as exc:
                state["status"] = "write_failed"
                state["repair_feedback"] = f"Writer error: {exc}"
                return state

            from app.services.skills import (
                build_verified_project_stacks,
                build_verified_skill_rail,
            )

            content = build_verified_project_stacks(
                content=content,
                evidence_records=evidence_records,
                job_description=jd,
            )
            content = build_verified_skill_rail(
                content=content,
                evidence_records=evidence_records,
                job_description=jd,
            )
            state["resume_content"] = content

            # Compile + validate ------------------------------------------- #
            pipeline_result = self._pipeline.run(
                header=header,
                content=content,
                evidence_records=evidence_records,
                output_directory=output_dir,
            )
            state["pipeline_result"] = pipeline_result
            state["issues"] = pipeline_result.issues

            if pipeline_result.status == "compile_failed":
                state["status"] = "compile_failed"
                return state

            if pipeline_result.passed:
                state["status"] = "passed"
                return state

            # Validation failure — build repair feedback ------------------- #
            repair_feedback = _repair_feedback_items(pipeline_result)
            state["repair_feedback"] = _build_repair_feedback(pipeline_result)

            if attempt >= max_total:
                break

        state["status"] = "needs_review"
        return state


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _source_count(
    evidence_records: tuple[EvidenceRecord, ...],
    *,
    source_types: set[str],
) -> int:
    return len(
        {
            record.source_id
            for record in evidence_records
            if record.source_type in source_types
        }
    )


def _validate_manifest_capacity(
    manifest: ResumeContentManifest,
    space_budget: ResumeSpaceBudget,
) -> None:
    from app.services.manifest import ContentManifestError

    capacities = (
        (
            "experience",
            len(manifest.experience_source_ids),
            space_budget.experience.entry_limit,
        ),
        (
            "projects",
            len(manifest.project_source_ids),
            space_budget.projects.entry_limit,
        ),
        (
            "education",
            len(manifest.education_source_ids),
            space_budget.education.entry_limit,
        ),
        (
            "skills",
            len(manifest.skill_names),
            _skill_capacity(space_budget=space_budget),
        ),
    )
    for section, requested, capacity in capacities:
        if requested > capacity:
            raise ContentManifestError(
                f"requested {requested} {section} but template capacity is {capacity}"
            )


def _default_content_requirements(
    *,
    template_id: ResumeTemplateId,
    available_projects: int,
    available_skills: int | None = None,
) -> ResumeContentRequirements:
    skill_count = _skill_capacity_for_template(template_id)
    if available_skills is not None:
        skill_count = min(skill_count, available_skills)
    return ResumeContentRequirements(
        project_count=min(5, available_projects),
        skill_count=skill_count,
    )


def _skill_capacity(*, space_budget: ResumeSpaceBudget) -> int:
    if space_budget.projects.entry_limit >= 6:
        return 80
    if space_budget.projects.entry_limit >= 3:
        return 32
    return 24


def _skill_capacity_for_template(template_id: ResumeTemplateId) -> int:
    if template_id == "deedy_cv_v1":
        return 80
    if template_id == "moderncv_two_column_v1":
        return 32
    return 24


def _skill_inventory_count(evidence_records: tuple[EvidenceRecord, ...]) -> int:
    return len(
        {
            skill.casefold()
            for record in evidence_records
            if record.allowed_for_resume
            for skill in record.skills
            if skill.strip()
        }
    )


def _apply_content_manifest(
    strategy: ResumeStrategy,
    manifest: ResumeContentManifest,
    evidence_records: tuple[EvidenceRecord, ...],
) -> ResumeStrategy:
    allowed = tuple(record for record in evidence_records if record.allowed_for_resume)
    experience_ids = _evidence_ids_for_sources(
        allowed, manifest.experience_source_ids, {"experience", "internship"}
    )
    project_ids = _evidence_ids_for_sources(
        allowed, manifest.project_source_ids, {"project"}
    )
    education_ids = _evidence_ids_for_sources(
        allowed, manifest.education_source_ids, {"education", "certification"}
    )
    skill_names = {skill.casefold() for skill in manifest.skill_names}
    skill_ids = tuple(
        record.evidence_id
        for record in allowed
        if record.source_type == "skill"
        and any(skill.casefold() in skill_names for skill in record.skills)
    )
    selected_ids = {
        *experience_ids,
        *project_ids,
        *education_ids,
        *skill_ids,
    }
    return strategy.model_copy(
        update={
            "selected_experience_evidence_ids": experience_ids,
            "selected_project_evidence_ids": project_ids,
            "selected_skill_evidence_ids": skill_ids,
            "selected_education_evidence_ids": education_ids,
            "omitted_evidence_ids": tuple(
                sorted(
                    record.evidence_id
                    for record in allowed
                    if record.evidence_id not in selected_ids
                )
            ),
        }
    )


def _evidence_ids_for_sources(
    records: tuple[EvidenceRecord, ...],
    source_ids: tuple[str, ...],
    source_types: set[str],
) -> tuple[str, ...]:
    wanted = set(source_ids)
    return tuple(
        record.evidence_id
        for record in records
        if record.source_id in wanted and record.source_type in source_types
    )


def _selected_evidence(
    strategy: object,
    evidence_records: tuple[EvidenceRecord, ...],
) -> tuple[EvidenceRecord, ...]:
    """Return only records referenced by the strategy."""
    from app.models import ResumeStrategy

    if not isinstance(strategy, ResumeStrategy):
        return evidence_records

    selected_ids = {
        *strategy.selected_experience_evidence_ids,
        *strategy.selected_project_evidence_ids,
        *strategy.selected_skill_evidence_ids,
        *strategy.selected_education_evidence_ids,
    }
    if not selected_ids:
        return evidence_records

    allowed = {r.evidence_id: r for r in evidence_records if r.allowed_for_resume}
    return tuple(allowed[eid] for eid in sorted(selected_ids) if eid in allowed)


def _build_repair_feedback(result: DeterministicPipelineResult) -> str:
    """Summarise validation issues into a concise repair instruction."""
    if not result.issues:
        return (
            "The previous draft failed validation "
            "— please produce a more compact draft."
        )
    parts = [f"- {issue.issue_type}: {issue.message}" for issue in result.issues[:5]]
    return "Fix the following validation issues in the next draft:\n" + "\n".join(parts)


def _repair_feedback_items(
    result: DeterministicPipelineResult,
) -> tuple[str, ...]:
    return tuple(f"{issue.issue_type}: {issue.message}" for issue in result.issues[:5])
