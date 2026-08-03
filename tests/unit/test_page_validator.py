from pathlib import Path

import pytest

from app.services.validation import PdfValidator


class StaticPdfInfoReader:
    def __init__(self, metadata: str) -> None:
        self.metadata = metadata
        self.requested_path: Path | None = None

    def read(self, pdf_path: Path) -> str:
        self.requested_path = pdf_path
        return self.metadata


@pytest.mark.unit
def test_page_validator_accepts_exactly_one_page(tmp_path: Path) -> None:
    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fixture")
    reader = StaticPdfInfoReader("Pages:           1\nPage size:       595 x 842 pts")

    report = PdfValidator(reader=reader).validate(pdf_path)

    assert report.passed is True
    assert report.page_count == 1
    assert report.issues == ()
    assert reader.requested_path == pdf_path


@pytest.mark.unit
def test_page_validator_rejects_two_page_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fixture")
    reader = StaticPdfInfoReader("Pages:           2\nPage size:       595 x 842 pts")

    report = PdfValidator(reader=reader).validate(pdf_path)

    assert report.passed is False
    assert report.page_count == 2
    assert len(report.issues) == 1
    assert report.issues[0].source == "geometry"
    assert report.issues[0].issue_type == "page_overflow"
    assert report.issues[0].severity == "fatal"
    assert report.issues[0].measured_value == 2
    assert report.issues[0].expected_value == 1


@pytest.mark.unit
def test_page_validator_reports_unparseable_pdf_metadata(tmp_path: Path) -> None:
    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(b"not a real PDF")
    reader = StaticPdfInfoReader("Syntax Error: Couldn't find trailer dictionary")

    report = PdfValidator(reader=reader).validate(pdf_path)

    assert report.passed is False
    assert report.page_count is None
    assert report.issues[0].source == "ats"
    assert report.issues[0].issue_type == "pdf_parse_error"
    assert report.issues[0].severity == "fatal"
