import pytest

from app.services.rendering import escape_latex


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
