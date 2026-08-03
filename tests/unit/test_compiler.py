import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from app.services.rendering import LatexCompiler, SubprocessRunner


class InvalidTexRunner:
    def __init__(self) -> None:
        self.command: tuple[str, ...] = ()
        self.cwd: Path | None = None
        self.timeout_seconds = 0.0

    def run(
        self, command: Sequence[str], *, cwd: Path, timeout_seconds: float
    ) -> subprocess.CompletedProcess[str]:
        self.command = tuple(command)
        self.cwd = cwd
        self.timeout_seconds = timeout_seconds
        return subprocess.CompletedProcess(
            args=command,
            returncode=1,
            stdout="This is pdfTeX",
            stderr="Undefined control sequence",
        )


class SuccessfulTexRunner(InvalidTexRunner):
    def run(
        self, command: Sequence[str], *, cwd: Path, timeout_seconds: float
    ) -> subprocess.CompletedProcess[str]:
        (cwd / "resume.pdf").write_bytes(b"%PDF-1.4 fixture")
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="Output written on resume.pdf",
            stderr="",
        )


class TimeoutRunner(InvalidTexRunner):
    def run(
        self, command: Sequence[str], *, cwd: Path, timeout_seconds: float
    ) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(
            command, timeout_seconds, output=b"partial log\xff"
        )


class MissingCompilerRunner(InvalidTexRunner):
    def run(
        self, command: Sequence[str], *, cwd: Path, timeout_seconds: float
    ) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("pdflatex")


@pytest.mark.unit
def test_compiler_returns_structured_failure_on_invalid_tex(tmp_path: Path) -> None:
    tex_path = tmp_path / "invalid.tex"
    tex_path.write_text(r"\invalidcommand", encoding="utf-8")
    runner = InvalidTexRunner()

    result = LatexCompiler(runner=runner).compile(tex_path)

    assert result.success is False
    assert result.error_type == "compilation_error"
    assert result.exit_code == 1
    assert result.pdf_path is None
    assert result.timed_out is False
    assert "Undefined control sequence" in result.log


@pytest.mark.unit
@pytest.mark.security
def test_compiler_disables_shell_escape_and_enforces_timeout(tmp_path: Path) -> None:
    tex_path = tmp_path / "resume.tex"
    tex_path.write_text(r"\documentclass{article}", encoding="utf-8")
    runner = InvalidTexRunner()

    LatexCompiler(runner=runner, timeout_seconds=7.5).compile(tex_path)

    assert runner.command == (
        "pdflatex",
        "-no-shell-escape",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "resume.tex",
    )
    assert runner.cwd == tmp_path
    assert runner.timeout_seconds == 7.5


@pytest.mark.unit
def test_compiler_returns_pdf_path_after_successful_process(tmp_path: Path) -> None:
    tex_path = tmp_path / "resume.tex"
    tex_path.write_text(r"\documentclass{article}", encoding="utf-8")

    result = LatexCompiler(runner=SuccessfulTexRunner()).compile(tex_path)

    assert result.success is True
    assert result.error_type is None
    assert result.pdf_path == str(tmp_path / "resume.pdf")


@pytest.mark.unit
def test_compiler_returns_structured_timeout(tmp_path: Path) -> None:
    tex_path = tmp_path / "resume.tex"
    tex_path.write_text(r"\documentclass{article}", encoding="utf-8")

    result = LatexCompiler(runner=TimeoutRunner()).compile(tex_path)

    assert result.success is False
    assert result.error_type == "timeout"
    assert result.timed_out is True
    assert "partial log" in result.log


@pytest.mark.unit
def test_process_runner_captures_output_without_a_command_shell(tmp_path: Path) -> None:
    result = SubprocessRunner().run(
        ("/usr/bin/printf", "compiler boundary"),
        cwd=tmp_path,
        timeout_seconds=2.0,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "compiler boundary"


@pytest.mark.unit
def test_compiler_returns_structured_failure_when_executable_is_missing(
    tmp_path: Path,
) -> None:
    tex_path = tmp_path / "resume.tex"
    tex_path.write_text(r"\documentclass{article}", encoding="utf-8")

    result = LatexCompiler(runner=MissingCompilerRunner()).compile(tex_path)

    assert result.success is False
    assert result.error_type == "compiler_unavailable"
    assert result.exit_code is None
