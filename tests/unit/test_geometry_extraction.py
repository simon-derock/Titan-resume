import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from app.services.validation import GeometryExtractionError, PdfGeometryExtractor


class RecordedBboxRunner:
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
def test_geometry_extractor_parses_page_and_word_bounds(tmp_path: Path) -> None:
    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fixture")
    runner = RecordedBboxRunner(
        """\
<html xmlns="http://www.w3.org/1999/xhtml">
  <body><doc><page width="595.28" height="841.89">
    <word xMin="24.0" yMin="20.0" xMax="60.0" yMax="32.0">Alex</word>
  </page></doc></body>
</html>
"""
    )

    geometry = PdfGeometryExtractor(runner=runner).extract(pdf_path)

    assert geometry.width_pt == 595.28
    assert geometry.height_pt == 841.89
    assert len(geometry.text_boxes) == 1
    assert geometry.text_boxes[0].element_id == "page.1.word.1"
    assert geometry.text_boxes[0].text == "Alex"
    assert geometry.text_boxes[0].x0 == 24.0
    assert runner.command == (
        "pdftotext",
        "-f",
        "1",
        "-l",
        "1",
        "-bbox",
        str(pdf_path),
        "-",
    )


@pytest.mark.unit
def test_geometry_extractor_rejects_malformed_bbox_output(tmp_path: Path) -> None:
    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fixture")

    with pytest.raises(GeometryExtractionError, match="bounding-box metadata"):
        PdfGeometryExtractor(runner=RecordedBboxRunner("not xml")).extract(pdf_path)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("metadata", "message"),
    [
        ("<html />", "does not contain a page"),
        (
            '<html><page width="595" height="842" /></html>',
            "does not contain text",
        ),
        (
            """\
<html><page width="595" height="842">
  <word yMin="20" xMax="40" yMax="30">Alex</word>
</page></html>
""",
            "is malformed",
        ),
    ],
)
def test_geometry_extractor_rejects_incomplete_bbox_metadata(
    tmp_path: Path, metadata: str, message: str
) -> None:
    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fixture")

    with pytest.raises(GeometryExtractionError, match=message):
        PdfGeometryExtractor(runner=RecordedBboxRunner(metadata)).extract(pdf_path)


@pytest.mark.unit
def test_geometry_extractor_reports_pdf_tool_failure(tmp_path: Path) -> None:
    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(b"not a PDF")

    with pytest.raises(GeometryExtractionError, match="could not be extracted"):
        PdfGeometryExtractor(runner=RecordedBboxRunner("", returncode=1)).extract(
            pdf_path
        )
