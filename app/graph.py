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
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TypedDict

from app.models import (
    DeterministicPipelineResult,
    EvidenceRecord,
    ResumeContent,
    ResumeHeader,
    ResumeTemplateId,
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
        evidence_records: object,
        output_directory: object,
    ) -> DeterministicPipelineResult: ...


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
        writer: _WriterClient,
        pipeline: _PipelineRunner,
        max_repair_cycles: int = 2,
    ) -> None:
        if not 1 <= max_repair_cycles <= _MAX_REPAIR_CYCLES_HARD_CAP:
            raise ValueError(
                f"max_repair_cycles must be between 1 and {_MAX_REPAIR_CYCLES_HARD_CAP}"
            )
        self._writer = writer
        self._pipeline = pipeline
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
        from app.services.matching import EvidenceMatcher
        from app.services.planning import SpacePlanner
        from app.services.strategy import ResumeStrategyBuilder

        try:
            ingested_jd = JobDescriptionIngester().ingest(raw_jd_text)
        except Exception as exc:
            state["status"] = "write_failed"
            state["repair_feedback"] = f"JD ingestion failed: {exc}"
            return state

        # Build a minimal StructuredJobDescription from evidence (offline path)
        # When a real JD analyzer is wired, replace this with analyzer.analyze()
        from app.models import StructuredJobDescription

        # Derive a minimal role label from the raw text for the offline path.
        # When a real JD analyzer is injected, it will replace this.
        _first_line = ingested_jd.raw_text.splitlines()[0].strip()[:120]
        jd = StructuredJobDescription(
            role=_first_line or "Engineer",
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
        strategy = ResumeStrategyBuilder().build(
            job_description=jd,
            evidence_matches=evidence_matches,
            evidence_records=evidence_records,
            space_budget=space_budget,
        )

        from app.models import ResumeWritingRequest

        # ------------------------------------------------------------------ #
        # Step 2 — write → compile → validate loop
        # ------------------------------------------------------------------ #
        max_total = self.max_repair_cycles + 1  # first attempt + repairs
        repair_feedback: str | None = None

        for attempt in range(1, max_total + 1):
            state["iteration"] = attempt

            # Build request (include repair feedback when available)
            request = ResumeWritingRequest(
                job_description=jd,
                strategy=strategy.model_copy(update={"omitted_evidence_ids": ()}),
                space_budget=space_budget,
                selected_evidence=_selected_evidence(strategy, evidence_records),
                template_id=template_id,
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
            repair_feedback = _build_repair_feedback(pipeline_result)
            state["repair_feedback"] = repair_feedback

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
