from pathlib import Path

import pytest

from app.models import GeometryPolicy, ResumeContent, ResumeHeader
from app.services.rendering import LatexCompiler, LatexRenderer
from app.services.validation import GeometryValidator, PdfGeometryExtractor

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TECTONIC_PATH = PROJECT_ROOT / ".tools" / "tectonic"
TECTONIC_CACHE_PATH = PROJECT_ROOT / ".tools" / "tectonic-cache"


@pytest.mark.integration
@pytest.mark.compiler
@pytest.mark.skipif(not TECTONIC_PATH.is_file(), reason="Tectonic is not installed")
def test_locked_pdf_exposes_real_safe_text_geometry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(TECTONIC_CACHE_PATH))
    tex_path = LatexRenderer().render(
        ResumeHeader(
            name="Alex Morgan",
            headline="AI Engineer",
            email="alex@example.com",
        ),
        ResumeContent(
            resume_id="resume.geometry_fixture.001",
            target_role="AI Engineer",
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

    geometry = PdfGeometryExtractor().extract(Path(compile_result.pdf_path))
    report = GeometryValidator(
        policy=GeometryPolicy(maximum_bottom_margin_pt=geometry.height_pt)
    ).validate(geometry)

    assert geometry.width_pt == pytest.approx(595.28, abs=0.1)
    assert geometry.height_pt == pytest.approx(841.89, abs=0.1)
    assert any(box.text == "Alex" for box in geometry.text_boxes)
    assert report.passed is True
