"""Safe transformation of structured resume content into LaTeX source."""

import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, Protocol

from jinja2 import FileSystemLoader, StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

from app.models import CompileResult, ResumeContent, ResumeHeader
from app.templates import get_template_profile

LATEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def escape_latex(text: str) -> str:
    """Escape candidate-controlled text without interpreting LaTeX commands."""

    return "".join(LATEX_ESCAPES.get(character, character) for character in text)


DEFAULT_TEMPLATE_DIRECTORY = Path(__file__).resolve().parents[2] / "templates"


class LatexRenderer:
    """Render validated content through the repository's locked template."""

    def __init__(self, template_directory: Path = DEFAULT_TEMPLATE_DIRECTORY) -> None:
        self._environment = SandboxedEnvironment(
            loader=FileSystemLoader(template_directory),
            undefined=StrictUndefined,
            autoescape=False,
            keep_trailing_newline=True,
        )
        self._environment.filters["latex"] = escape_latex

    def render(
        self, header: ResumeHeader, content: ResumeContent, output_path: Path
    ) -> Path:
        """Write deterministic LaTeX source and return its artifact path."""

        profile = get_template_profile(content.template_id)
        template = self._environment.get_template(profile.template_file)
        source = template.render(header=header, resume=content)
        output_path.write_text(source, encoding="utf-8")
        return output_path


class ProcessRunner(Protocol):
    """Replaceable boundary for invoking the system LaTeX process."""

    def run(
        self, command: Sequence[str], *, cwd: Path, timeout_seconds: float
    ) -> subprocess.CompletedProcess[str]: ...


class SubprocessRunner:
    """Production process runner that never invokes a command shell."""

    def run(
        self, command: Sequence[str], *, cwd: Path, timeout_seconds: float
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(command),
            cwd=cwd,
            timeout=timeout_seconds,
            check=False,
            capture_output=True,
            text=True,
        )


class LatexCompiler:
    """Compile one rendered source file under fixed security constraints."""

    def __init__(
        self,
        *,
        runner: ProcessRunner | None = None,
        executable: str = "pdflatex",
        engine: Literal["pdflatex", "tectonic"] = "pdflatex",
        timeout_seconds: float = 20.0,
    ) -> None:
        self._runner = runner or SubprocessRunner()
        self._executable = executable
        self._engine = engine
        self._timeout_seconds = timeout_seconds

    def compile(self, tex_path: Path) -> CompileResult:
        command = self._command(tex_path)
        try:
            process = self._runner.run(
                command,
                cwd=tex_path.parent,
                timeout_seconds=self._timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            log = _process_log(exc.stdout, exc.stderr)
            return CompileResult(
                success=False,
                exit_code=None,
                pdf_path=None,
                log=log,
                timed_out=True,
                error_type="timeout",
            )
        except FileNotFoundError as exc:
            return CompileResult(
                success=False,
                exit_code=None,
                pdf_path=None,
                log=str(exc),
                error_type="compiler_unavailable",
            )

        pdf_path = tex_path.with_suffix(".pdf")
        success = process.returncode == 0 and pdf_path.is_file()
        return CompileResult(
            success=success,
            exit_code=process.returncode,
            pdf_path=str(pdf_path) if success else None,
            log=_process_log(process.stdout, process.stderr),
            error_type=None if success else "compilation_error",
        )

    def _command(self, tex_path: Path) -> tuple[str, ...]:
        if self._engine == "tectonic":
            return (
                self._executable,
                "--untrusted",
                "--only-cached",
                "--keep-logs",
                "--outdir",
                str(tex_path.parent),
                tex_path.name,
            )
        return (
            self._executable,
            "-no-shell-escape",
            "-interaction=nonstopmode",
            "-halt-on-error",
            tex_path.name,
        )


def _process_log(stdout: str | bytes | None, stderr: str | bytes | None) -> str:
    """Combine subprocess streams into stable text for structured diagnostics."""

    def as_text(value: str | bytes | None) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value or ""

    return "\n".join(part for part in (as_text(stdout), as_text(stderr)) if part)


class ScreenshotRenderError(RuntimeError):
    """Raised when the deterministic PDF rasterizer cannot create a preview."""


class PdfScreenshotRenderer:
    """Render the first PDF page to a high-resolution PNG preview."""

    def __init__(
        self,
        *,
        runner: ProcessRunner | None = None,
        executable: str = "pdftoppm",
        dpi: int = 200,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._runner = runner or SubprocessRunner()
        self._executable = executable
        self._dpi = dpi
        self._timeout_seconds = timeout_seconds

    def render_first_page(self, pdf_path: Path, output_path: Path) -> Path:
        output_prefix = output_path.with_suffix("")
        command = (
            self._executable,
            "-f",
            "1",
            "-l",
            "1",
            "-singlefile",
            "-png",
            "-r",
            str(self._dpi),
            str(pdf_path),
            str(output_prefix),
        )
        process = self._runner.run(
            command,
            cwd=pdf_path.parent,
            timeout_seconds=self._timeout_seconds,
        )
        if process.returncode != 0 or not output_path.is_file():
            raise ScreenshotRenderError(_process_log(process.stdout, process.stderr))
        return output_path
