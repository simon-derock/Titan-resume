import pytest

from app.models import BenchmarkEvaluationRecord
from app.services.evaluation import EvaluationReportBuilder


def _record(
    *,
    benchmark_id: str,
    status: str,
    passed: bool,
    compile_success: bool,
    exactly_one_page: bool,
    ats_text_extractable: bool,
    ats_reading_order_valid: bool,
    geometry_passed: bool,
    unsupported_claim_count: int,
    repair_iterations: int,
    elapsed_seconds: float,
    page_fill_percent: float | None,
) -> BenchmarkEvaluationRecord:
    return BenchmarkEvaluationRecord(
        benchmark_id=benchmark_id,
        platform="google_careers",
        role="AI Engineer",
        company="Example",
        template_id="deedy_cv_v1",
        status=status,
        passed=passed,
        compile_success=compile_success,
        exactly_one_page=exactly_one_page,
        ats_text_extractable=ats_text_extractable,
        ats_reading_order_valid=ats_reading_order_valid,
        geometry_passed=geometry_passed,
        unsupported_claim_count=unsupported_claim_count,
        repair_iterations=repair_iterations,
        elapsed_seconds=elapsed_seconds,
        page_fill_percent=page_fill_percent,
        linked_entry_count=6 if passed else 0,
    )


@pytest.mark.unit
def test_evaluation_report_aggregates_reproducible_quality_metrics() -> None:
    records = (
        _record(
            benchmark_id="job.zeta",
            status="validation_failed",
            passed=False,
            compile_success=False,
            exactly_one_page=False,
            ats_text_extractable=False,
            ats_reading_order_valid=False,
            geometry_passed=False,
            unsupported_claim_count=1,
            repair_iterations=2,
            elapsed_seconds=20.0,
            page_fill_percent=None,
        ),
        _record(
            benchmark_id="job.alpha",
            status="passed",
            passed=True,
            compile_success=True,
            exactly_one_page=True,
            ats_text_extractable=True,
            ats_reading_order_valid=True,
            geometry_passed=True,
            unsupported_claim_count=0,
            repair_iterations=1,
            elapsed_seconds=10.0,
            page_fill_percent=94.0,
        ),
    )

    report = EvaluationReportBuilder().build(records)

    assert report.schema_version == 1
    assert report.benchmark_count == 2
    assert report.passed_count == 1
    assert report.pass_rate_percent == 50.0
    assert report.compile_success_rate_percent == 50.0
    assert report.exactly_one_page_rate_percent == 50.0
    assert report.ats_text_extraction_rate_percent == 50.0
    assert report.ats_reading_order_rate_percent == 50.0
    assert report.geometry_pass_rate_percent == 50.0
    assert report.unsupported_claim_rate_percent == 50.0
    assert report.average_repair_iterations == 1.5
    assert report.average_elapsed_seconds == 15.0
    assert report.average_page_fill_percent == 94.0
    assert tuple(record.benchmark_id for record in report.records) == (
        "job.alpha",
        "job.zeta",
    )


@pytest.mark.unit
def test_evaluation_report_rejects_an_empty_benchmark_run() -> None:
    with pytest.raises(ValueError, match="at least one benchmark record"):
        EvaluationReportBuilder().build(())
