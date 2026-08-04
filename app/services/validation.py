"""Deterministic quality gates for compiled resume artifacts."""

import re
import subprocess
from pathlib import Path
from typing import Protocol

from app.models import (
    GeometryPolicy,
    GeometryReport,
    PageGeometry,
    PdfValidationReport,
    TextBox,
    ValidationIssue,
)


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
        issues = tuple(
            self._unsafe_margin_issue(
                edge=edge,
                box=boxes[edge],
                measured_value=measured_value,
                expected_value=thresholds[edge],
            )
            for edge, measured_value in margins.items()
            if measured_value < thresholds[edge]
        )
        return GeometryReport(
            passed=not issues,
            minimum_left_margin_pt=margins["left"],
            minimum_right_margin_pt=margins["right"],
            minimum_top_margin_pt=margins["top"],
            minimum_bottom_margin_pt=margins["bottom"],
            issues=issues,
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
