from pathlib import Path

import pytest

from app.models import (
    EvidenceText,
    ResumeContent,
    ResumeEntry,
    ResumeHeader,
)
from app.services.rendering import LatexCompiler, LatexRenderer
from app.services.validation import AtsTextValidator, PdfTextExtractor

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TECTONIC_PATH = PROJECT_ROOT / ".tools" / "tectonic"
TECTONIC_CACHE_PATH = PROJECT_ROOT / ".tools" / "tectonic-cache"
EXPECTED_SECTIONS = ("Summary", "Experience", "Projects", "Skills", "Education")
EVIDENCE_ID = "project.titan.001"


@pytest.mark.integration
@pytest.mark.compiler
@pytest.mark.skipif(not TECTONIC_PATH.is_file(), reason="Tectonic is not installed")
def test_locked_pdf_exposes_ats_text_in_logical_section_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(TECTONIC_CACHE_PATH))
    entry = ResumeEntry(
        element_id="experience.titan",
        heading="TITAN",
        subheading="AI Engineer",
        evidence_ids=(EVIDENCE_ID,),
    )
    tex_path = LatexRenderer().render(
        ResumeHeader(
            name="Alex Morgan",
            headline="AI Engineer",
            email="alex@example.com",
        ),
        ResumeContent(
            resume_id="resume.ats_fixture.001",
            target_role="AI Engineer",
            summary=EvidenceText(
                element_id="summary",
                text="Builds reliable AI systems.",
                evidence_ids=(EVIDENCE_ID,),
            ),
            experience=(entry,),
            projects=(entry.model_copy(update={"element_id": "projects.titan"}),),
            skills=(
                EvidenceText(
                    element_id="skills.languages",
                    text="Languages: Python",
                    evidence_ids=(EVIDENCE_ID,),
                ),
            ),
            education=(
                entry.model_copy(
                    update={
                        "element_id": "education.degree",
                        "heading": "B.Tech Computer Science",
                    }
                ),
            ),
        ),
        tmp_path / "resume.tex",
    )
    compile_result = LatexCompiler(
        executable=str(TECTONIC_PATH),
        engine="tectonic",
        timeout_seconds=120.0,
    ).compile(tex_path)
    assert compile_result.success is True, compile_result.log
    assert compile_result.pdf_path is not None

    extracted_text = PdfTextExtractor().extract(Path(compile_result.pdf_path))
    report = AtsTextValidator(expected_sections=EXPECTED_SECTIONS).validate(
        extracted_text
    )

    assert "Alex Morgan" in extracted_text
    assert report.passed is True
