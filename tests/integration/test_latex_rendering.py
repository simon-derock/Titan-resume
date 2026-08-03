from pathlib import Path

import pytest

from app.models import EvidenceText, ResumeContent, ResumeEntry, ResumeHeader
from app.services.rendering import LatexRenderer


@pytest.mark.integration
@pytest.mark.security
def test_structured_resume_renders_through_locked_template(tmp_path: Path) -> None:
    header = ResumeHeader(
        name=r"Alex \input{secrets}",
        headline="AI Engineer & Agent Architect",
        location="Chennai, India",
        email="alex@example.com",
        phone="+91 99999 99999",
        linkedin="https://linkedin.com/in/alex",
        github="https://github.com/alex",
    )
    content = ResumeContent(
        resume_id="resume.ai_engineer.001",
        target_role="AI Engineer",
        summary=EvidenceText(
            element_id="summary",
            text="Builds evidence-grounded R&D systems with 100% traceability.",
            evidence_ids=("project.titan.001",),
        ),
        projects=(
            ResumeEntry(
                element_id="projects.titan",
                heading="TITAN",
                subheading="Self-Correcting Resume Compiler",
                evidence_ids=("project.titan.001",),
            ),
        ),
        skills=(
            EvidenceText(
                element_id="skills.languages",
                text="Languages: Python & SQL",
                evidence_ids=("project.titan.001",),
            ),
        ),
    )
    output_path = tmp_path / "resume.tex"

    rendered_path = LatexRenderer().render(header, content, output_path)

    source = rendered_path.read_text(encoding="utf-8")
    assert rendered_path == output_path
    assert "% TITAN-TEMPLATE: resume_v1" in source
    assert "% TITAN-ELEMENT: summary" in source
    assert r"Alex \textbackslash{}input\{secrets\}" in source
    assert r"AI Engineer \& Agent Architect" in source
    assert r"R\&D systems with 100\% traceability" in source
    assert r"\input{secrets}" not in source
