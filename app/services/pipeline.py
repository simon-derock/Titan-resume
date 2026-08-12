"""Deterministic resume compilation and artifact-validation pipeline."""

from collections.abc import Iterable
from pathlib import Path

from app.models import (
    DeterministicPipelineResult,
    EvidenceRecord,
    GeometryPolicy,
    ResumeContent,
    ResumeHeader,
    validate_resume_content_evidence,
)
from app.services.rendering import LatexCompiler, LatexRenderer, PdfScreenshotRenderer
from app.services.validation import (
    AtsTextValidator,
    GeometryValidator,
    PdfGeometryExtractor,
    PdfTextExtractor,
    PdfValidator,
)


class DeterministicResumePipeline:
    """Compose the tested document engine without model or network calls."""

    def __init__(
        self,
        *,
        compiler: LatexCompiler,
        expected_sections: tuple[str, ...],
        renderer: LatexRenderer | None = None,
        page_validator: PdfValidator | None = None,
        text_extractor: PdfTextExtractor | None = None,
        geometry_extractor: PdfGeometryExtractor | None = None,
        screenshot_renderer: PdfScreenshotRenderer | None = None,
        geometry_validator: GeometryValidator | None = None,
    ) -> None:
        self._compiler = compiler
        self._expected_sections = expected_sections
        self._renderer = renderer or LatexRenderer()
        self._page_validator = page_validator or PdfValidator()
        self._text_extractor = text_extractor or PdfTextExtractor()
        self._geometry_extractor = geometry_extractor or PdfGeometryExtractor()
        self._screenshot_renderer = screenshot_renderer or PdfScreenshotRenderer()
        self._geometry_validator = geometry_validator or GeometryValidator(
            policy=GeometryPolicy()
        )

    def run(
        self,
        header: ResumeHeader,
        content: ResumeContent,
        evidence_records: Iterable[EvidenceRecord],
        output_directory: Path,
    ) -> DeterministicPipelineResult:
        validate_resume_content_evidence(content, evidence_records)
        tex_path = self._renderer.render(
            header,
            content,
            output_directory / "resume.tex",
        )
        compile_result = self._compiler.compile(tex_path)
        if not compile_result.success or compile_result.pdf_path is None:
            return DeterministicPipelineResult(
                status="compile_failed",
                passed=False,
                tex_path=str(tex_path),
                compile_result=compile_result,
            )

        pdf_path = Path(compile_result.pdf_path)
        page_report = self._page_validator.validate(pdf_path)
        if not page_report.passed:
            return DeterministicPipelineResult(
                status="validation_failed",
                passed=False,
                tex_path=str(tex_path),
                pdf_path=str(pdf_path),
                compile_result=compile_result,
                page_report=page_report,
                issues=page_report.issues,
            )

        extracted_text = self._text_extractor.extract(pdf_path)
        ats_report = AtsTextValidator(
            expected_sections=_ats_section_order(
                self._expected_sections,
                template_id=content.template_id,
            ),
            column_section_orders=_ats_column_section_orders(
                self._expected_sections,
                template_id=content.template_id,
            ),
        ).validate(extracted_text)
        geometry = self._geometry_extractor.extract(pdf_path)
        geometry_report = self._geometry_validator.validate(
            geometry,
            template_id=content.template_id,
        )
        screenshot_path = self._screenshot_renderer.render_first_page(
            pdf_path, output_directory / "resume.png"
        )
        issues = (*ats_report.issues, *geometry_report.issues)
        passed = not issues
        return DeterministicPipelineResult(
            status="passed" if passed else "validation_failed",
            passed=passed,
            tex_path=str(tex_path),
            pdf_path=str(pdf_path),
            screenshot_path=str(screenshot_path),
            compile_result=compile_result,
            page_report=page_report,
            ats_report=ats_report,
            geometry_report=geometry_report,
            issues=issues,
        )


def _ats_section_order(
    expected_sections: tuple[str, ...],
    *,
    template_id: str,
) -> tuple[str, ...]:
    if template_id != "deedy_cv_v1":
        return expected_sections

    physical_order = {
        section: index
        for index, section in enumerate(
            ("summary", "skills", "experience", "education", "projects")
        )
    }
    return tuple(
        sorted(
            expected_sections,
            key=lambda section: physical_order.get(
                section.casefold(), len(physical_order)
            ),
        )
    )


def _ats_column_section_orders(
    expected_sections: tuple[str, ...],
    *,
    template_id: str,
) -> tuple[tuple[str, ...], ...]:
    if template_id != "deedy_cv_v1":
        return ()
    expected = {section.casefold(): section for section in expected_sections}
    orders = (
        ("summary", "skills", "education"),
        ("summary", "experience", "projects"),
    )
    return tuple(
        tuple(expected[section] for section in order if section in expected)
        for order in orders
    )
