from datetime import date
from pathlib import Path

import pytest

from app.models import EvidenceRecord, EvidenceText, ResumeContent, ResumeHeader
from app.services.pipeline import DeterministicResumePipeline
from app.services.rendering import LatexCompiler

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TECTONIC_PATH = PROJECT_ROOT / ".tools" / "tectonic"
TECTONIC_CACHE_PATH = PROJECT_ROOT / ".tools" / "tectonic-cache"


@pytest.mark.integration
@pytest.mark.compiler
@pytest.mark.skipif(not TECTONIC_PATH.is_file(), reason="Tectonic is not installed")
def test_deterministic_pipeline_returns_all_validated_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(TECTONIC_CACHE_PATH))
    evidence = EvidenceRecord(
        evidence_id="project.titan.001",
        source_type="project",
        source_id="titan",
        claim="Built TITAN.",
        confidence=1.0,
        allowed_for_resume=True,
        last_verified_at=date(2026, 8, 4),
    )
    content = ResumeContent(
        resume_id="resume.pipeline.001",
        target_role="AI Engineer",
        summary=EvidenceText(
            element_id="summary",
            text="Builds reliable AI systems.",
            evidence_ids=(evidence.evidence_id,),
        ),
    )
    pipeline = DeterministicResumePipeline(
        compiler=LatexCompiler(
            executable=str(TECTONIC_PATH),
            engine="tectonic",
            timeout_seconds=120.0,
        ),
        expected_sections=("Summary",),
    )

    result = pipeline.run(
        ResumeHeader(name="Alex Morgan", headline="AI Engineer"),
        content,
        (evidence,),
        tmp_path,
    )

    assert result.passed is True
    assert result.status == "passed"
    assert Path(result.tex_path).is_file()
    assert result.pdf_path is not None and Path(result.pdf_path).is_file()
    assert result.screenshot_path is not None
    assert Path(result.screenshot_path).read_bytes().startswith(b"\x89PNG")
    assert result.page_report is not None and result.page_report.page_count == 1
    assert result.ats_report is not None and result.ats_report.passed is True
    assert result.geometry_report is not None
    assert result.geometry_report.passed is True
    assert result.issues == ()
