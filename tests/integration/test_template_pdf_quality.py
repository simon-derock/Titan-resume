from pathlib import Path

import pytest

from app.models import (
    EvidenceText,
    GeometryPolicy,
    ResumeBullet,
    ResumeContent,
    ResumeEntry,
    ResumeHeader,
)
from app.services.rendering import LatexCompiler, LatexRenderer
from app.services.validation import (
    GeometryValidator,
    PdfGeometryExtractor,
    PdfTextExtractor,
    PdfValidator,
)
from app.templates import SUPPORTED_TEMPLATE_IDS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TECTONIC_PATH = PROJECT_ROOT / ".tools" / "tectonic"
TECTONIC_CACHE_PATH = PROJECT_ROOT / ".tools" / "tectonic-cache"
EVIDENCE_ID = "project.titan.001"


def representative_content(template_id: str) -> ResumeContent:
    bullet = ResumeBullet(
        element_id="experience.titan.compiler",
        text="Built a deterministic resume compiler with evidence validation.",
        evidence_ids=(EVIDENCE_ID,),
        target_max_lines=2,
    )
    entry = ResumeEntry(
        element_id="experience.titan",
        heading="TITAN",
        subheading="AI Engineer",
        location="Chennai, India",
        date_range="2025-2026",
        evidence_ids=(EVIDENCE_ID,),
        bullets=(bullet,),
    )
    return ResumeContent(
        resume_id="resume.template_quality.001",
        target_role="AI Engineer",
        summary=EvidenceText(
            element_id="summary.main",
            text="AI engineer building reliable, evidence-grounded systems.",
            evidence_ids=(EVIDENCE_ID,),
        ),
        experience=(entry,),
        projects=(
            entry.model_copy(
                update={
                    "element_id": "projects.titan",
                    "subheading": "Self-Correcting Resume Compiler",
                }
            ),
        ),
        skills=(
            EvidenceText(
                element_id="skills.primary",
                text="Python, Pydantic, Jinja2, LaTeX",
                evidence_ids=(EVIDENCE_ID,),
            ),
        ),
        education=(
            entry.model_copy(
                update={
                    "element_id": "education.degree",
                    "heading": "B.Tech in AI and Data Science",
                    "subheading": "Engineering University",
                    "bullets": (),
                }
            ),
        ),
        template_id=template_id,
    )


@pytest.mark.integration
@pytest.mark.compiler
@pytest.mark.parametrize("template_id", SUPPORTED_TEMPLATE_IDS)
@pytest.mark.skipif(not TECTONIC_PATH.is_file(), reason="Tectonic is not installed")
def test_supported_template_produces_a_safe_extractable_one_page_pdf(
    template_id: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(TECTONIC_CACHE_PATH))
    tex_path = LatexRenderer().render(
        ResumeHeader(
            name="Alex Morgan",
            headline="AI Engineer",
            email="alex@example.com",
            github="https://github.com/alex",
        ),
        representative_content(template_id),
        tmp_path / "resume.tex",
    )

    compile_result = LatexCompiler(
        executable=str(TECTONIC_PATH),
        engine="tectonic",
        timeout_seconds=120.0,
    ).compile(tex_path)

    assert compile_result.success is True, compile_result.log
    assert compile_result.pdf_path is not None
    pdf_path = Path(compile_result.pdf_path)
    assert PdfValidator().validate(pdf_path).passed is True

    extracted_text = PdfTextExtractor().extract(pdf_path)
    for expected_text in (
        "Alex Morgan",
        "Summary",
        "Experience",
        "Projects",
        "Skills",
        "Education",
    ):
        assert expected_text.lower() in extracted_text.lower()

    geometry = PdfGeometryExtractor().extract(pdf_path)
    geometry_report = GeometryValidator(policy=GeometryPolicy()).validate(geometry)
    assert geometry_report.passed is True, geometry_report.issues
