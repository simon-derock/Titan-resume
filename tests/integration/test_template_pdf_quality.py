import subprocess
from datetime import date
from pathlib import Path

import pytest

from app.models import (
    EvidenceRecord,
    EvidenceText,
    GeometryPolicy,
    ResumeBullet,
    ResumeContent,
    ResumeEntry,
    ResumeHeader,
)
from app.services.pipeline import DeterministicResumePipeline
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
                    "url": "https://github.com/alex/titan",
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
    url_report = subprocess.run(
        ("pdfinfo", "-url", str(pdf_path)),
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "https://github.com/alex/titan" in url_report

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
    geometry_report = GeometryValidator(
        policy=GeometryPolicy(maximum_bottom_margin_pt=geometry.height_pt)
    ).validate(geometry)
    assert geometry_report.passed is True, geometry_report.issues


@pytest.mark.integration
@pytest.mark.compiler
@pytest.mark.skipif(not TECTONIC_PATH.is_file(), reason="Tectonic is not installed")
def test_deedy_pipeline_validates_its_physical_column_reading_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(TECTONIC_CACHE_PATH))
    content = representative_content("deedy_cv_v1")
    evidence = EvidenceRecord(
        evidence_id=EVIDENCE_ID,
        source_type="project",
        source_id="project.titan",
        claim="Built a deterministic resume compiler with evidence validation.",
        evidence_url="https://github.com/alex/titan",
        confidence=1.0,
        allowed_for_resume=True,
        last_verified_at=date(2026, 8, 11),
    )
    pipeline = DeterministicResumePipeline(
        compiler=LatexCompiler(
            executable=str(TECTONIC_PATH),
            engine="tectonic",
            timeout_seconds=120.0,
        ),
        expected_sections=(
            "summary",
            "experience",
            "projects",
            "skills",
            "education",
        ),
        geometry_validator=GeometryValidator(
            policy=GeometryPolicy(maximum_bottom_margin_pt=842.0)
        ),
    )

    result = pipeline.run(
        ResumeHeader(name="Alex Morgan", headline="AI Engineer"),
        content,
        (evidence,),
        tmp_path,
    )

    assert result.ats_report is not None
    assert result.ats_report.reading_order_valid is True
    assert result.passed is True


@pytest.mark.integration
@pytest.mark.compiler
@pytest.mark.skipif(not TECTONIC_PATH.is_file(), reason="Tectonic is not installed")
def test_deedy_dense_resume_reaches_reviewed_page_fill(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A complete 5/6/1 resume should fill at least 93% of its A4 height."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(TECTONIC_CACHE_PATH))

    def entry(section: str, index: int, text: str) -> ResumeEntry:
        return ResumeEntry(
            element_id=f"{section}.{index}",
            heading=f"{section.title()} {index}",
            subheading="AI Engineer" if section == "experience" else None,
            date_range="2025-2026" if section == "experience" else None,
            evidence_ids=(EVIDENCE_ID,),
            bullets=(
                ResumeBullet(
                    element_id=f"{section}.{index}.bullet",
                    text=text,
                    evidence_ids=(EVIDENCE_ID,),
                    target_max_lines=2,
                ),
            ),
        )

    experience_texts = (
        "Engineered production agent infrastructure using LangGraph, hybrid "
        "retrieval, and FastAPI services.",
        "Developed an LLM coding copilot that helped engineers write cleaner "
        "and faster Python code.",
        "Built workflow automation for real-time document processing and "
        "autonomous agent task execution.",
        "Created healthcare prediction models using feature engineering and "
        "statistical modelling.",
        "Completed practical training in cybersecurity essentials and network "
        "security fundamentals.",
    )
    project_texts = (
        "Architected an asynchronous ReAct engine integrating eight agents, "
        "vector memory, and model routing.",
        "Fine-tuned an open model on clinical samples and deployed offline "
        "inference to mobile hardware.",
        "Designed a decoupled multi-agent RAG pipeline with message-bus "
        "orchestration and vector retrieval.",
        "Deployed a headless AI server with embeddings, conversational memory, "
        "and local model inference.",
        "Built a real-time player tracker using detection, Kalman filtering, "
        "and assignment optimization.",
        "Shipped an email classifier as a FastAPI service for automated "
        "support-ticket processing.",
    )
    content = ResumeContent(
        resume_id="resume.dense.001",
        target_role="AI Engineer",
        summary=EvidenceText(
            element_id="summary.main",
            text=(
                "AI Engineer building production agentic RAG, multi-agent systems, "
                "and reliable Python services with grounded model evaluation."
            ),
            evidence_ids=(EVIDENCE_ID,),
        ),
        experience=tuple(
            entry("experience", index, text)
            for index, text in enumerate(experience_texts, start=1)
        ),
        projects=tuple(
            entry("project", index, text)
            for index, text in enumerate(project_texts, start=1)
        ),
        skills=(
            EvidenceText(
                element_id="skills.main",
                text=(
                    "Python, FastAPI, LangGraph, LangChain, PyTorch, OpenCV, "
                    "Agentic RAG, Multi-Agent Systems, Qdrant, ChromaDB, Zilliz, "
                    "Ollama, Linux, Streamlit, MySQL"
                ),
                evidence_ids=(EVIDENCE_ID,),
            ),
        ),
        education=(
            ResumeEntry(
                element_id="education.degree",
                heading="B.Tech in Artificial Intelligence and Data Science",
                subheading="Engineering University",
                date_range="2021-2025",
                location="Coimbatore, India",
                evidence_ids=(EVIDENCE_ID,),
            ),
        ),
        template_id="deedy_cv_v1",
    )
    tex_path = LatexRenderer().render(
        ResumeHeader(name="Alex Morgan", headline="AI Engineer"),
        content,
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
    geometry = PdfGeometryExtractor().extract(pdf_path)
    report = GeometryValidator(
        policy=GeometryPolicy(maximum_bottom_margin_pt=60.0)
    ).validate(geometry)
    assert report.passed is True, report.issues
