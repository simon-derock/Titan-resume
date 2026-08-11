"""Deterministic quality gates for compiled resume artifacts."""

import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Protocol

from app.models import (
    AtsValidationReport,
    GeometryPolicy,
    GeometryReport,
    PageGeometry,
    PdfValidationReport,
    TextBox,
    ValidationIssue,
)
from app.services.rendering import ProcessRunner, SubprocessRunner


class PdfInfoReader(Protocol):
    """Boundary for obtaining parseable metadata from a PDF artifact."""

    def read(self, pdf_path: Path) -> str: ...


PAGE_COUNT_PATTERN = re.compile(r"(?m)^Pages:\s*(\d+)\s*$")


class SubprocessPdfInfoReader:
    """Read PDF metadata with fixed arguments and no command shell."""

    def __init__(self, *, executable: str = "pdfinfo", timeout_seconds: float = 10.0):
        self._executable = executable
        self._timeout_seconds = timeout_seconds

    def read(self, pdf_path: Path) -> str:
        process = subprocess.run(
            [self._executable, str(pdf_path)],
            cwd=pdf_path.parent,
            timeout=self._timeout_seconds,
            check=False,
            capture_output=True,
            text=True,
        )
        return "\n".join(part for part in (process.stdout, process.stderr) if part)


class PdfValidator:
    """Enforce hard artifact invariants without model judgment."""

    def __init__(self, *, reader: PdfInfoReader | None = None) -> None:
        self._reader = reader or SubprocessPdfInfoReader()

    def validate(self, pdf_path: Path) -> PdfValidationReport:
        metadata = self._reader.read(pdf_path)
        page_match = PAGE_COUNT_PATTERN.search(metadata)
        if page_match is None:
            issue = ValidationIssue(
                issue_id="pdf.metadata.parse_error",
                source="ats",
                issue_type="pdf_parse_error",
                severity="fatal",
                message="PDF page metadata could not be parsed.",
                recommended_action="Recompile the artifact and inspect compiler logs.",
            )
            return PdfValidationReport(
                passed=False,
                page_count=None,
                issues=(issue,),
            )

        page_count = int(page_match.group(1))
        if page_count == 1:
            return PdfValidationReport(passed=True, page_count=page_count)

        issue = ValidationIssue(
            issue_id="pdf.page_count.overflow",
            source="geometry",
            issue_type="page_overflow",
            severity="fatal",
            message=f"Resume contains {page_count} pages; exactly one is required.",
            recommended_action="Compress the lowest-priority content.",
            measured_value=page_count,
            expected_value=1,
        )
        return PdfValidationReport(
            passed=False,
            page_count=page_count,
            issues=(issue,),
        )


class GeometryValidator:
    """Veto text boxes that cross configured safe page margins."""

    def __init__(self, *, policy: GeometryPolicy) -> None:
        self._policy = policy

    def validate(self, geometry: PageGeometry) -> GeometryReport:
        left_box = min(geometry.text_boxes, key=lambda box: box.x0)
        right_box = max(geometry.text_boxes, key=lambda box: box.x1)
        top_box = min(geometry.text_boxes, key=lambda box: box.y0)
        bottom_box = max(geometry.text_boxes, key=lambda box: box.y1)

        margins = {
            "left": left_box.x0,
            "right": geometry.width_pt - right_box.x1,
            "top": top_box.y0,
            "bottom": geometry.height_pt - bottom_box.y1,
        }
        boxes: dict[str, TextBox] = {
            "left": left_box,
            "right": right_box,
            "top": top_box,
            "bottom": bottom_box,
        }
        thresholds = {
            "left": self._policy.minimum_horizontal_margin_pt,
            "right": self._policy.minimum_horizontal_margin_pt,
            "top": self._policy.minimum_top_margin_pt,
            "bottom": self._policy.minimum_bottom_margin_pt,
        }
        issues = [
            self._unsafe_margin_issue(
                edge=edge,
                box=boxes[edge],
                measured_value=measured_value,
                expected_value=thresholds[edge],
            )
            for edge, measured_value in margins.items()
            if measured_value < thresholds[edge]
        ]
        if margins["bottom"] > self._policy.maximum_bottom_margin_pt:
            issues.append(
                self._excessive_bottom_whitespace_issue(
                    box=bottom_box,
                    measured_value=margins["bottom"],
                    expected_value=self._policy.maximum_bottom_margin_pt,
                )
            )
        return GeometryReport(
            passed=not issues,
            minimum_left_margin_pt=margins["left"],
            minimum_right_margin_pt=margins["right"],
            minimum_top_margin_pt=margins["top"],
            minimum_bottom_margin_pt=margins["bottom"],
            issues=tuple(issues),
        )

    @staticmethod
    def _unsafe_margin_issue(
        *, edge: str, box: TextBox, measured_value: float, expected_value: float
    ) -> ValidationIssue:
        return ValidationIssue(
            issue_id=f"geometry.margin.{edge}.{box.element_id}",
            source="geometry",
            element_id=box.element_id,
            issue_type="unsafe_margin",
            severity="fatal",
            message=f"Text crosses the safe {edge} margin.",
            recommended_action="Adjust the affected content or safe layout tokens.",
            measured_value=measured_value,
            expected_value=expected_value,
        )

    @staticmethod
    def _excessive_bottom_whitespace_issue(
        *, box: TextBox, measured_value: float, expected_value: float
    ) -> ValidationIssue:
        return ValidationIssue(
            issue_id=f"geometry.underfill.{box.element_id}",
            source="geometry",
            element_id=box.element_id,
            issue_type="excessive_bottom_whitespace",
            severity="high",
            message="Resume leaves too much unused space at the bottom of the page.",
            recommended_action=(
                "Restore the highest-value omitted evidence before adding filler or "
                "changing typography."
            ),
            measured_value=measured_value,
            expected_value=expected_value,
        )


class GeometryExtractionError(RuntimeError):
    """Raised when PDF word coordinates cannot be extracted safely."""


class PdfGeometryExtractor:
    """Extract first-page word bounds through Poppler's XHTML output."""

    def __init__(
        self,
        *,
        runner: ProcessRunner | None = None,
        executable: str = "pdftotext",
        timeout_seconds: float = 10.0,
    ) -> None:
        self._runner = runner or SubprocessRunner()
        self._executable = executable
        self._timeout_seconds = timeout_seconds

    def extract(self, pdf_path: Path) -> PageGeometry:
        command = (
            self._executable,
            "-f",
            "1",
            "-l",
            "1",
            "-bbox",
            str(pdf_path),
            "-",
        )
        process = self._runner.run(
            command,
            cwd=pdf_path.parent,
            timeout_seconds=self._timeout_seconds,
        )
        if process.returncode != 0:
            raise GeometryExtractionError(
                "PDF bounding-box metadata could not be extracted."
            )

        try:
            root = ET.fromstring(process.stdout)
            page = root.find(".//{*}page")
            if page is None:
                raise GeometryExtractionError(
                    "PDF bounding-box metadata does not contain a page."
                )
            text_boxes = tuple(
                TextBox(
                    element_id=f"page.1.word.{index}",
                    text="".join(word.itertext()),
                    x0=float(word.attrib["xMin"]),
                    y0=float(word.attrib["yMin"]),
                    x1=float(word.attrib["xMax"]),
                    y1=float(word.attrib["yMax"]),
                )
                for index, word in enumerate(page.findall(".//{*}word"), start=1)
            )
            if not text_boxes:
                raise GeometryExtractionError(
                    "PDF bounding-box metadata does not contain text."
                )
            return PageGeometry(
                width_pt=float(page.attrib["width"]),
                height_pt=float(page.attrib["height"]),
                text_boxes=text_boxes,
            )
        except (ET.ParseError, KeyError, ValueError) as exc:
            raise GeometryExtractionError(
                "PDF bounding-box metadata is malformed."
            ) from exc


class TextExtractionError(RuntimeError):
    """Raised when ATS-readable text cannot be obtained from a PDF."""


class PdfTextExtractor:
    """Extract first-page text in visual layout order through Poppler."""

    def __init__(
        self,
        *,
        runner: ProcessRunner | None = None,
        executable: str = "pdftotext",
        timeout_seconds: float = 10.0,
    ) -> None:
        self._runner = runner or SubprocessRunner()
        self._executable = executable
        self._timeout_seconds = timeout_seconds

    def extract(self, pdf_path: Path) -> str:
        command = (
            self._executable,
            "-f",
            "1",
            "-l",
            "1",
            "-layout",
            str(pdf_path),
            "-",
        )
        process = self._runner.run(
            command,
            cwd=pdf_path.parent,
            timeout_seconds=self._timeout_seconds,
        )
        if process.returncode != 0:
            raise TextExtractionError("ATS text could not be extracted from the PDF.")
        return process.stdout


class AtsTextValidator:
    """Validate extracted text presence and configured section order."""

    def __init__(self, *, expected_sections: tuple[str, ...]) -> None:
        self._expected_sections = expected_sections

    def validate(self, extracted_text: str) -> AtsValidationReport:
        if not extracted_text.strip():
            issue = ValidationIssue(
                issue_id="ats.text.missing",
                source="ats",
                issue_type="ats_text_missing",
                severity="fatal",
                message="The compiled PDF does not expose extractable text.",
                recommended_action="Inspect fonts and PDF text encoding.",
            )
            return AtsValidationReport(
                passed=False,
                text_extractable=False,
                reading_order_valid=False,
                issues=(issue,),
            )

        section_positions: list[int] = []
        for section in self._expected_sections:
            position = _section_heading_position(extracted_text, section)
            if position < 0:
                issue = ValidationIssue(
                    issue_id=f"ats.section.missing.{section.lower()}",
                    source="ats",
                    issue_type="reading_order_invalid",
                    severity="fatal",
                    message=f"Expected section is missing: {section}.",
                    recommended_action="Restore the required section heading.",
                )
                return AtsValidationReport(
                    passed=False,
                    text_extractable=True,
                    reading_order_valid=False,
                    issues=(issue,),
                )
            section_positions.append(position)

        reading_order_valid = section_positions == sorted(section_positions)
        if not reading_order_valid:
            issue = ValidationIssue(
                issue_id="ats.section.reading_order",
                source="ats",
                issue_type="reading_order_invalid",
                severity="fatal",
                message="Resume sections are not in the configured reading order.",
                recommended_action="Restore the configured template section order.",
            )
            return AtsValidationReport(
                passed=False,
                text_extractable=True,
                reading_order_valid=False,
                issues=(issue,),
            )

        return AtsValidationReport(
            passed=True,
            text_extractable=True,
            reading_order_valid=True,
        )


def _section_heading_position(extracted_text: str, section: str) -> int:
    heading = re.compile(
        rf"(?im)(?:^[ \t]*|[ \t]{{2,}}){re.escape(section)}"
        rf"(?=[ \t]*(?:$|[ \t]{{2,}}))"
    )
    match = heading.search(extracted_text)
    return -1 if match is None else match.start()
