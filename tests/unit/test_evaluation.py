import json
from pathlib import Path

import pytest

from app.graph import ResumeGraphState
from app.models import (
    AtsValidationReport,
    BenchmarkEvaluationRecord,
    CompileResult,
    DeterministicPipelineResult,
    GeometryReport,
    PdfValidationReport,
    ResumeContent,
    ResumeEntry,
)
from app.services.evaluation import (
    EvaluationRecordBuilder,
    EvaluationReportBuilder,
    EvaluationReportWriter,
)


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


@pytest.mark.unit
def test_evaluation_record_measures_a_terminal_graph_result() -> None:
    content = ResumeContent(
        resume_id="resume.google.001",
        target_role="Software Engineer III, GenAI",
        template_id="deedy_cv_v1",
        projects=(
            ResumeEntry(
                element_id="projects.xphil",
                heading="XPHIL",
                url="https://example.com/xphil",
                evidence_ids=("evidence.project.xphil",),
            ),
        ),
    )
    pipeline_result = DeterministicPipelineResult(
        status="passed",
        passed=True,
        tex_path="outputs/google/resume.tex",
        pdf_path="outputs/google/resume.pdf",
        screenshot_path="outputs/google/resume.png",
        compile_result=CompileResult(
            success=True,
            exit_code=0,
            pdf_path="outputs/google/resume.pdf",
            log="",
        ),
        page_report=PdfValidationReport(passed=True, page_count=1),
        ats_report=AtsValidationReport(
            passed=True,
            text_extractable=True,
            reading_order_valid=True,
        ),
        geometry_report=GeometryReport(
            passed=True,
            minimum_left_margin_pt=28.0,
            minimum_right_margin_pt=28.0,
            minimum_top_margin_pt=24.0,
            minimum_bottom_margin_pt=50.75,
        ),
    )
    state: ResumeGraphState = {
        "request_id": "google_software_engineer_iii_genai",
        "raw_jd_text": "Google GenAI role",
        "status": "passed",
        "iteration": 2,
        "max_repair_cycles": 2,
        "pipeline_result": pipeline_result,
        "issues": (),
        "resume_content": content,
        "repair_feedback": None,
    }

    record = EvaluationRecordBuilder().from_graph_state(
        benchmark_id="google_software_engineer_iii_genai",
        platform="google_careers",
        role="Software Engineer III, GenAI",
        company="Google Cloud",
        template_id="deedy_cv_v1",
        elapsed_seconds=42.25,
        state=state,
    )

    assert record.passed is True
    assert record.compile_success is True
    assert record.exactly_one_page is True
    assert record.ats_text_extractable is True
    assert record.ats_reading_order_valid is True
    assert record.geometry_passed is True
    assert record.unsupported_claim_count == 0
    assert record.repair_iterations == 1
    assert record.elapsed_seconds == 42.25
    assert record.page_fill_percent == 93.97
    assert record.linked_entry_count == 1


@pytest.mark.unit
def test_evaluation_report_writer_persists_stable_json(tmp_path: Path) -> None:
    report = EvaluationReportBuilder().build(
        (
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
                repair_iterations=0,
                elapsed_seconds=12.5,
                page_fill_percent=95.0,
            ),
        )
    )

    output_path = EvaluationReportWriter().write(
        report,
        tmp_path / "nested" / "evaluation.json",
    )

    assert output_path.is_file()
    assert output_path.read_text(encoding="utf-8").endswith("\n")
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["benchmark_count"] == 1
    assert payload["records"][0]["benchmark_id"] == "job.alpha"
