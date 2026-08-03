from pathlib import Path

import pytest

from app.services.rendering import LatexCompiler
from app.services.validation import PdfValidator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TECTONIC_PATH = PROJECT_ROOT / ".tools" / "tectonic"
TECTONIC_CACHE_PATH = PROJECT_ROOT / ".tools" / "tectonic-cache"


@pytest.mark.integration
@pytest.mark.compiler
@pytest.mark.skipif(not TECTONIC_PATH.is_file(), reason="Tectonic is not installed")
def test_real_two_page_pdf_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(TECTONIC_CACHE_PATH))
    tex_path = tmp_path / "two_pages.tex"
    tex_path.write_text(
        """\
\\documentclass{article}
\\begin{document}
First page
\\newpage
Second page
\\end{document}
""",
        encoding="utf-8",
    )
    compile_result = LatexCompiler(
        executable=str(TECTONIC_PATH),
        engine="tectonic",
        timeout_seconds=120.0,
    ).compile(tex_path)
    assert compile_result.success is True, compile_result.log
    assert compile_result.pdf_path is not None

    report = PdfValidator().validate(Path(compile_result.pdf_path))

    assert report.passed is False
    assert report.page_count == 2
    assert report.issues[0].issue_type == "page_overflow"
    assert report.issues[0].severity == "fatal"
