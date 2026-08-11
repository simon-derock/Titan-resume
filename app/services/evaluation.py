"""Deterministic aggregation for reproducible resume benchmark reports."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from statistics import fmean
from time import perf_counter
from typing import Literal, Protocol, cast

from app.graph import ResumeGraphState
from app.models import (
    BenchmarkCorpus,
    BenchmarkEvaluationRecord,
    EvaluationReport,
    EvidenceRecord,
    ResumeHeader,
    ResumeTemplateId,
)

_A4_HEIGHT_PT = 841.8898
_BenchmarkStatus = Literal[
    "passed",
    "validation_failed",
    "compile_failed",
    "needs_review",
    "write_failed",
]
_ALLOWED_BENCHMARK_STATUSES: frozenset[str] = frozenset(
    {
        "passed",
        "validation_failed",
        "compile_failed",
        "needs_review",
        "write_failed",
    }
)


class _GraphExecutor(Protocol):
    def run(
        self,
        *,
        raw_jd_text: str,
        header: ResumeHeader,
        evidence_records: tuple[EvidenceRecord, ...],
        output_dir: Path,
        template_id: ResumeTemplateId,
        request_id: str,
    ) -> ResumeGraphState: ...


class BenchmarkEvaluator:
    """Run a fixed typed corpus through an injected resume graph executor."""

    def __init__(
        self,
        *,
        executor: _GraphExecutor,
        clock: Callable[[], float] = perf_counter,
        record_builder: EvaluationRecordBuilder | None = None,
        report_builder: EvaluationReportBuilder | None = None,
    ) -> None:
        self._executor = executor
        self._clock = clock
        self._record_builder = record_builder or EvaluationRecordBuilder()
        self._report_builder = report_builder or EvaluationReportBuilder()

    def run(
        self,
        *,
        corpus: BenchmarkCorpus,
        header: ResumeHeader,
        evidence_records: tuple[EvidenceRecord, ...],
        output_root: Path,
        template_id: ResumeTemplateId,
    ) -> EvaluationReport:
        records: list[BenchmarkEvaluationRecord] = []
        for job in corpus.jobs:
            output_dir = output_root / job.benchmark_id
            output_dir.mkdir(parents=True, exist_ok=True)
            started_at = self._clock()
            state = self._executor.run(
                raw_jd_text=job.raw_text,
                header=header,
                evidence_records=evidence_records,
                output_dir=output_dir,
                template_id=template_id,
                request_id=job.benchmark_id,
            )
            elapsed_seconds = max(self._clock() - started_at, 0.0)
            records.append(
                self._record_builder.from_graph_state(
                    benchmark_id=job.benchmark_id,
                    platform=job.platform,
                    role=job.role,
                    company=job.company,
                    template_id=template_id,
                    elapsed_seconds=elapsed_seconds,
                    state=state,
                )
            )
        return self._report_builder.build(records)


class EvaluationRecordBuilder:
    """Measure one terminal graph state without reopening its PDF artifacts."""

    def from_graph_state(
        self,
        *,
        benchmark_id: str,
        platform: str,
        role: str,
        company: str,
        template_id: ResumeTemplateId,
        elapsed_seconds: float,
        state: ResumeGraphState,
    ) -> BenchmarkEvaluationRecord:
        status_value = state["status"]
        if status_value not in _ALLOWED_BENCHMARK_STATUSES:
            raise ValueError(f"unsupported benchmark status: {status_value}")
        status = cast(_BenchmarkStatus, status_value)

        pipeline_result = state.get("pipeline_result")
        page_report = pipeline_result.page_report if pipeline_result else None
        ats_report = pipeline_result.ats_report if pipeline_result else None
        geometry_report = pipeline_result.geometry_report if pipeline_result else None
        issues = state.get("issues", ())
        content = state.get("resume_content")

        linked_entry_count = 0
        if content is not None:
            linked_entry_count = sum(
                entry.url is not None
                for entry in (
                    *content.experience,
                    *content.projects,
                    *content.education,
                )
            )

        return BenchmarkEvaluationRecord(
            benchmark_id=benchmark_id,
            platform=platform,
            role=role,
            company=company,
            template_id=template_id,
            status=status,
            passed=bool(
                status == "passed"
                and pipeline_result is not None
                and pipeline_result.passed
            ),
            compile_success=bool(
                pipeline_result is not None and pipeline_result.compile_result.success
            ),
            exactly_one_page=bool(
                page_report is not None
                and page_report.passed
                and page_report.page_count == 1
            ),
            ats_text_extractable=bool(
                ats_report is not None and ats_report.text_extractable
            ),
            ats_reading_order_valid=bool(
                ats_report is not None and ats_report.reading_order_valid
            ),
            geometry_passed=bool(
                geometry_report is not None and geometry_report.passed
            ),
            unsupported_claim_count=sum(
                issue.source == "provenance" or issue.issue_type == "unsupported_claim"
                for issue in issues
            ),
            repair_iterations=max(state.get("iteration", 0) - 1, 0),
            elapsed_seconds=elapsed_seconds,
            page_fill_percent=_page_fill_percent(
                geometry_report.minimum_bottom_margin_pt
                if geometry_report is not None
                else None
            ),
            linked_entry_count=linked_entry_count,
            issue_types=tuple(sorted({issue.issue_type for issue in issues})),
        )


class EvaluationReportWriter:
    """Persist one report as stable, newline-terminated JSON."""

    def write(self, report: EvaluationReport, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
        temporary_path.write_text(
            f"{report.model_dump_json(indent=2)}\n",
            encoding="utf-8",
        )
        temporary_path.replace(output_path)
        return output_path


class EvaluationReportBuilder:
    """Aggregate typed per-JD measurements without external I/O."""

    def build(
        self,
        records: Iterable[BenchmarkEvaluationRecord],
    ) -> EvaluationReport:
        ordered_records = tuple(sorted(records, key=lambda record: record.benchmark_id))
        if not ordered_records:
            raise ValueError("at least one benchmark record is required")

        page_fill_values = tuple(
            record.page_fill_percent
            for record in ordered_records
            if record.page_fill_percent is not None
        )
        return EvaluationReport(
            benchmark_count=len(ordered_records),
            passed_count=sum(record.passed for record in ordered_records),
            pass_rate_percent=_rate(ordered_records, "passed"),
            compile_success_rate_percent=_rate(
                ordered_records,
                "compile_success",
            ),
            exactly_one_page_rate_percent=_rate(
                ordered_records,
                "exactly_one_page",
            ),
            ats_text_extraction_rate_percent=_rate(
                ordered_records,
                "ats_text_extractable",
            ),
            ats_reading_order_rate_percent=_rate(
                ordered_records,
                "ats_reading_order_valid",
            ),
            geometry_pass_rate_percent=_rate(
                ordered_records,
                "geometry_passed",
            ),
            unsupported_claim_rate_percent=_unsupported_claim_rate(ordered_records),
            average_repair_iterations=_mean(
                record.repair_iterations for record in ordered_records
            ),
            average_elapsed_seconds=_mean(
                record.elapsed_seconds for record in ordered_records
            ),
            average_page_fill_percent=(
                _mean(page_fill_values) if page_fill_values else None
            ),
            records=ordered_records,
        )


def _rate(
    records: tuple[BenchmarkEvaluationRecord, ...],
    field_name: str,
) -> float:
    passing = sum(bool(getattr(record, field_name)) for record in records)
    return round(passing / len(records) * 100.0, 4)


def _unsupported_claim_rate(
    records: tuple[BenchmarkEvaluationRecord, ...],
) -> float:
    affected = sum(record.unsupported_claim_count > 0 for record in records)
    return round(affected / len(records) * 100.0, 4)


def _mean(values: Iterable[int | float]) -> float:
    return round(fmean(values), 4)


def _page_fill_percent(bottom_margin_pt: float | None) -> float | None:
    if bottom_margin_pt is None:
        return None
    measured = (_A4_HEIGHT_PT - bottom_margin_pt) / _A4_HEIGHT_PT * 100.0
    return round(min(max(measured, 0.0), 100.0), 2)
