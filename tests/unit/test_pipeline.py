import subprocess
from collections.abc import Sequence
from datetime import date
from pathlib import Path

import pytest

from app.models import EvidenceRecord, EvidenceText, ResumeContent, ResumeHeader
from app.services.pipeline import DeterministicResumePipeline
from app.services.rendering import LatexCompiler
from app.services.validation import PdfValidator


class CompileFailureRunner:
    def run(
        self, command: Sequence[str], *, cwd: Path, timeout_seconds: float
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, "", "invalid TeX")


class CompileSuccessRunner:
    def run(
        self, command: Sequence[str], *, cwd: Path, timeout_seconds: float
    ) -> subprocess.CompletedProcess[str]:
        (cwd / "resume.pdf").write_bytes(b"%PDF-1.4 fixture")
        return subprocess.CompletedProcess(command, 0, "compiled", "")


class StaticPdfInfoReader:
    def __init__(self, page_count: int) -> None:
        self.page_count = page_count

    def read(self, pdf_path: Path) -> str:
        return f"Pages: {self.page_count}"


def evidence() -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id="project.titan.001",
        source_type="project",
        source_id="titan",
        claim="Built TITAN.",
        confidence=1.0,
        allowed_for_resume=True,
        last_verified_at=date(2026, 8, 4),
    )


def header() -> ResumeHeader:
    return ResumeHeader(name="Alex Morgan", headline="AI Engineer")


def content() -> ResumeContent:
    return ResumeContent(
        resume_id="resume.pipeline.001",
        target_role="AI Engineer",
        summary=EvidenceText(
            element_id="summary",
            text="Builds reliable AI systems.",
            evidence_ids=("project.titan.001",),
        ),
    )


@pytest.mark.unit
def test_pipeline_returns_structured_compile_failure_without_downstream_artifacts(
    tmp_path: Path,
) -> None:
    pipeline = DeterministicResumePipeline(
        compiler=LatexCompiler(runner=CompileFailureRunner()),
        expected_sections=("Summary",),
    )

    result = pipeline.run(header(), content(), (evidence(),), tmp_path)

    assert result.passed is False
    assert result.status == "compile_failed"
    assert result.compile_result.error_type == "compilation_error"
    assert result.pdf_path is None
    assert result.screenshot_path is None
    assert result.page_report is None


@pytest.mark.unit
def test_pipeline_stops_when_page_count_gate_fails(tmp_path: Path) -> None:
    pipeline = DeterministicResumePipeline(
        compiler=LatexCompiler(runner=CompileSuccessRunner()),
        page_validator=PdfValidator(reader=StaticPdfInfoReader(page_count=2)),
        expected_sections=("Summary",),
    )

    result = pipeline.run(header(), content(), (evidence(),), tmp_path)

    assert result.passed is False
    assert result.status == "validation_failed"
    assert result.page_report is not None
    assert result.page_report.page_count == 2
    assert result.issues[0].issue_type == "page_overflow"
    assert result.ats_report is None
    assert result.geometry_report is None
