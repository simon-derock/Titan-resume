import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from app.services.validation import (
    AtsTextValidator,
    PdfTextExtractor,
    TextExtractionError,
)

EXPECTED_SECTIONS = ("Summary", "Experience", "Projects", "Skills", "Education")


class RecordedTextRunner:
    def __init__(self, output: str, returncode: int = 0) -> None:
        self.output = output
        self.returncode = returncode
        self.command: tuple[str, ...] = ()

    def run(
        self, command: Sequence[str], *, cwd: Path, timeout_seconds: float
    ) -> subprocess.CompletedProcess[str]:
        self.command = tuple(command)
        return subprocess.CompletedProcess(command, self.returncode, self.output, "")


@pytest.mark.unit
def test_ats_validator_accepts_extractable_text_in_logical_order() -> None:
    extracted_text = "\n".join(("Alex Morgan", *EXPECTED_SECTIONS))

    report = AtsTextValidator(expected_sections=EXPECTED_SECTIONS).validate(
        extracted_text
    )

    assert report.passed is True
    assert report.text_extractable is True
    assert report.reading_order_valid is True
    assert report.issues == ()


@pytest.mark.unit
def test_ats_validator_ignores_section_words_inside_resume_prose() -> None:
    extracted_text = "\n".join(
        (
            "SUMMARY",
            "AI engineer delivering projects with production experience and rigor.",
            "EXPERIENCE",
            "Built reliable agent services.",
            "PROJECTS",
            "Grounded resume compiler.",
            "SKILLS",
            "Python, LangGraph",
            "EDUCATION",
            "B.Tech Artificial Intelligence",
        )
    )

    report = AtsTextValidator(expected_sections=EXPECTED_SECTIONS).validate(
        extracted_text
    )

    assert report.passed is True
    assert report.reading_order_valid is True


@pytest.mark.unit
def test_ats_validator_rejects_blank_extracted_text() -> None:
    report = AtsTextValidator(expected_sections=EXPECTED_SECTIONS).validate(" \n\t")

    assert report.passed is False
    assert report.text_extractable is False
    assert report.reading_order_valid is False
    assert report.issues[0].source == "ats"
    assert report.issues[0].issue_type == "ats_text_missing"
    assert report.issues[0].severity == "fatal"


@pytest.mark.unit
def test_ats_validator_rejects_invalid_section_reading_order() -> None:
    extracted_text = "\n".join(
        ("Alex Morgan", "Projects", "Experience", "Skills", "Education")
    )

    report = AtsTextValidator(expected_sections=EXPECTED_SECTIONS[1:]).validate(
        extracted_text
    )

    assert report.passed is False
    assert report.text_extractable is True
    assert report.reading_order_valid is False
    assert report.issues[0].issue_type == "reading_order_invalid"
    assert report.issues[0].severity == "fatal"


@pytest.mark.unit
def test_ats_validator_reports_missing_expected_section() -> None:
    extracted_text = "Alex Morgan\nSummary\nProjects\nSkills\nEducation"

    report = AtsTextValidator(expected_sections=EXPECTED_SECTIONS).validate(
        extracted_text
    )

    assert report.passed is False
    assert report.reading_order_valid is False
    assert report.issues[0].issue_type == "reading_order_invalid"
    assert report.issues[0].message == "Expected section is missing: Experience."


@pytest.mark.unit
def test_ats_validator_accepts_interleaved_two_column_section_order() -> None:
    extracted_text = """SUMMARY
AI Engineer building grounded systems.
SKILLS                                        EXPERIENCE
ENGINEERING                                   BLACKCOAT AI
Python                                        Built agent workflows.
LLM & AGENTIC AI                              PROJECTS
LangGraph                                     TITAN
EDUCATION                                     Built a compiler.
B.Tech Artificial Intelligence
"""

    report = AtsTextValidator(
        expected_sections=EXPECTED_SECTIONS,
        column_section_orders=(
            ("Summary", "Skills", "Education"),
            ("Summary", "Experience", "Projects"),
        ),
    ).validate(extracted_text)

    assert report.passed is True
    assert report.text_extractable is True
    assert report.reading_order_valid is True


@pytest.mark.unit
def test_pdf_text_extractor_uses_first_page_layout_mode(tmp_path: Path) -> None:
    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fixture")
    runner = RecordedTextRunner("Alex Morgan\nAI Engineer")

    extracted_text = PdfTextExtractor(runner=runner).extract(pdf_path)

    assert extracted_text == "Alex Morgan\nAI Engineer"
    assert runner.command == (
        "pdftotext",
        "-f",
        "1",
        "-l",
        "1",
        "-layout",
        str(pdf_path),
        "-",
    )


@pytest.mark.unit
def test_pdf_text_extractor_reports_tool_failure(tmp_path: Path) -> None:
    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(b"not a PDF")

    with pytest.raises(TextExtractionError, match="could not be extracted"):
        PdfTextExtractor(runner=RecordedTextRunner("", returncode=1)).extract(pdf_path)
