"""Safe transformation of structured resume content into LaTeX source."""

from pathlib import Path

from jinja2 import FileSystemLoader, StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

from app.models import ResumeContent, ResumeHeader

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

        template = self._environment.get_template(f"{content.template_id}.tex.j2")
        source = template.render(header=header, resume=content)
        output_path.write_text(source, encoding="utf-8")
        return output_path
