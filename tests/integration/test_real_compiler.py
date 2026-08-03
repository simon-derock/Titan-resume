from pathlib import Path

import pytest

from app.models import ResumeContent, ResumeHeader
from app.services.rendering import LatexCompiler, LatexRenderer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TECTONIC_PATH = PROJECT_ROOT / ".tools" / "tectonic"
TECTONIC_CACHE_PATH = PROJECT_ROOT / ".tools" / "tectonic-cache"


@pytest.mark.integration
@pytest.mark.compiler
@pytest.mark.skipif(not TECTONIC_PATH.is_file(), reason="Tectonic is not installed")
def test_locked_template_compiles_to_real_pdf(
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
            resume_id="resume.compiler_fixture.001",
            target_role="AI Engineer",
        ),
        tmp_path / "resume.tex",
    )

    result = LatexCompiler(
        executable=str(TECTONIC_PATH),
        engine="tectonic",
        timeout_seconds=120.0,
    ).compile(tex_path)

    assert result.success is True, result.log
    assert result.pdf_path == str(tmp_path / "resume.pdf")
    assert Path(result.pdf_path).read_bytes().startswith(b"%PDF-")
