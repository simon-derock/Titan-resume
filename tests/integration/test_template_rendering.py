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
