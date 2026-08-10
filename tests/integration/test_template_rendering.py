from pathlib import Path

import pytest

from app.models import EvidenceText, ResumeContent, ResumeEntry, ResumeHeader
from app.services.rendering import LatexRenderer
from app.templates import SUPPORTED_TEMPLATE_IDS


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.parametrize("template_id", SUPPORTED_TEMPLATE_IDS)
def test_selected_template_renders_only_escaped_structured_content(
    template_id: str,
    tmp_path: Path,
) -> None:
    evidence_id = "project.titan.001"
    entry = ResumeEntry(
        element_id="experience.titan",
        heading=r"TITAN \input{private}",
        subheading="AI Engineer & Architect",
        location="Chennai, India",
        date_range="2025-2026",
        evidence_ids=(evidence_id,),
    )
    content = ResumeContent(
        resume_id="resume.template_rendering.001",
        target_role="AI Engineer",
        summary=EvidenceText(
            element_id="summary.main",
            text="Builds reliable R&D systems.",
            evidence_ids=(evidence_id,),
        ),
        experience=(entry,),
        projects=(entry.model_copy(update={"element_id": "projects.titan"}),),
        skills=(
            EvidenceText(
                element_id="skills.primary",
                text="Python & SQL",
                evidence_ids=(evidence_id,),
            ),
        ),
        education=(
            entry.model_copy(
                update={
                    "element_id": "education.degree",
                    "heading": "B.Tech in AI & Data Science",
                }
            ),
        ),
        template_id=template_id,
    )

    rendered_path = LatexRenderer().render(
        ResumeHeader(
            name="Alex Morgan",
            headline="AI Engineer",
            email="alex@example.com",
        ),
        content,
        tmp_path / "resume.tex",
    )

    source = rendered_path.read_text(encoding="utf-8")
    assert f"% TITAN-TEMPLATE: {template_id}" in source
    assert "% TITAN-ELEMENT: summary.main" in source
    assert r"TITAN \textbackslash{}input\{private\}" in source
    assert r"AI Engineer \& Architect" in source
    assert r"\input{private}" not in source


@pytest.mark.integration
@pytest.mark.parametrize("template_id", SUPPORTED_TEMPLATE_IDS)
def test_templates_share_fixed_full_width_identity_header(
    template_id: str,
    tmp_path: Path,
) -> None:
    evidence_id = "evidence.header.001"
    content = ResumeContent(
        resume_id="resume.shared_header.001",
        target_role="AI Engineer",
        summary=EvidenceText(
            element_id="summary.main",
            text="Builds grounded production AI systems.",
            evidence_ids=(evidence_id,),
        ),
        template_id=template_id,
    )

    rendered_path = LatexRenderer().render(
        ResumeHeader(
            name="Alex Morgan",
            headline="AI Engineer | Agentic AI Specialist",
            location="Bengaluru, India",
            email="alex@example.com",
            phone="+91 8300057632",
            linkedin="linkedin.com/in/alex",
            github="github.com/alex",
            portfolio="alex.example.com",
        ),
        content,
        tmp_path / "resume.tex",
    )

    source = rendered_path.read_text(encoding="utf-8")
    assert source.count("% TITAN-ELEMENT: header") == 1
    assert source.count(r"\section{Summary}") == 1
    assert r"\fontsize{30}{32}\selectfont" in source
    assert r"\href{mailto:alex@example.com}{alex@example.com}" in source
    assert r"\href{tel:+918300057632}{+91 8300057632}" in source
    assert r"\href{https://linkedin.com/in/alex}{LinkedIn}" in source
    assert r"\href{https://github.com/alex}{GitHub}" in source
    assert r"\href{https://alex.example.com}{Portfolio}" in source
    if template_id != "resume_v1":
        assert source.index(r"\section{Summary}") < source.index(
            r"\begin{minipage}"
        )
