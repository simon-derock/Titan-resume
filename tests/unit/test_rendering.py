import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from app.services.rendering import (
    PdfScreenshotRenderer,
    ScreenshotRenderError,
    escape_latex,
)


class FailedRasterRunner:
    def __init__(self) -> None:
        self.command: tuple[str, ...] = ()

    def run(
        self, command: Sequence[str], *, cwd: Path, timeout_seconds: float
    ) -> subprocess.CompletedProcess[str]:
        self.command = tuple(command)
        return subprocess.CompletedProcess(command, 1, "", "raster failed")


@pytest.mark.unit
@pytest.mark.security
def test_renderer_escapes_latex_special_characters() -> None:
    candidate_text = "R&D_#1 earned $50% {verified} ~ ^ \\"

    escaped = escape_latex(candidate_text)

    assert escaped == (
        r"R\&D\_\#1 earned \$50\% \{verified\} "
        r"\textasciitilde{} \textasciicircum{} \textbackslash{}"
    )


@pytest.mark.unit
@pytest.mark.security
def test_renderer_neutralizes_latex_command_injection() -> None:
    escaped = escape_latex(r"\input{/etc/passwd}")

    assert escaped == r"\textbackslash{}input\{/etc/passwd\}"
    assert r"\input" not in escaped


@pytest.mark.unit
def test_renderer_maps_resume_unicode_to_supported_latex_glyphs() -> None:
    escaped = escape_latex("Aug 2025 – May 2026 — ₹8,000…")

    assert escaped == r"Aug 2025 -- May 2026 --- INR~8,000\ldots{}"


@pytest.mark.unit
def test_screenshot_renderer_returns_explicit_failure_for_raster_error(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fixture")
    runner = FailedRasterRunner()

    with pytest.raises(ScreenshotRenderError, match="raster failed"):
        PdfScreenshotRenderer(runner=runner, dpi=200).render_first_page(
            pdf_path, tmp_path / "resume.png"
        )

    assert runner.command == (
        "pdftoppm",
        "-f",
        "1",
        "-l",
        "1",
        "-singlefile",
        "-png",
        "-r",
        "200",
        str(pdf_path),
        str(tmp_path / "resume"),
    )
