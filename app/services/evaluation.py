"""Deterministic aggregation for reproducible resume benchmark reports."""

from collections.abc import Iterable
from statistics import fmean

from app.models import BenchmarkEvaluationRecord, EvaluationReport


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
