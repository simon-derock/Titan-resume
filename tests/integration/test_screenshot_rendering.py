import struct
from pathlib import Path

import pytest

from app.models import ResumeContent, ResumeHeader
from app.services.rendering import LatexCompiler, LatexRenderer, PdfScreenshotRenderer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TECTONIC_PATH = PROJECT_ROOT / ".tools" / "tectonic"
TECTONIC_CACHE_PATH = PROJECT_ROOT / ".tools" / "tectonic-cache"


@pytest.mark.integration
@pytest.mark.compiler
@pytest.mark.visual
@pytest.mark.skipif(not TECTONIC_PATH.is_file(), reason="Tectonic is not installed")
def test_first_page_screenshot_preserves_a4_ratio_at_high_resolution(
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
            resume_id="resume.screenshot_fixture.001",
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

    screenshot_path = PdfScreenshotRenderer(dpi=200).render_first_page(
        Path(compile_result.pdf_path), tmp_path / "resume.png"
    )

    png = screenshot_path.read_bytes()
    width, height = struct.unpack(">II", png[16:24])
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert width >= 1600
    assert height >= 2300
    assert width / height == pytest.approx(210 / 297, abs=0.002)
