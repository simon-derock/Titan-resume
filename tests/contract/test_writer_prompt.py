"""Contract: versioned writer prompt must satisfy all grounded-writing constraints.

These tests define the minimum required shape and content of the writer prompt.
They do not call any live model.  They fail until app/prompts/writer_v1.py is
implemented correctly.
"""

import pytest

EVIDENCE_ID = "evidence.experience.titan"


# ---------------------------------------------------------------------------
# Helpers — imported lazily so the RED import failure is the test failure
# ---------------------------------------------------------------------------


def _import_prompt_module():  # pragma: no cover
    from app.prompts import writer_v1

    return writer_v1


def _build_minimal_request():  # pragma: no cover
    from datetime import date

    from app.models import (
        EvidenceRecord,
        ResumeSpaceBudget,
        ResumeStrategy,
        ResumeWritingRequest,
        SectionSpaceBudget,
        StructuredJobDescription,
    )

    jd = StructuredJobDescription(
        role="Senior ML Engineer",
        must_have_skills=("Python", "PyTorch"),
        raw_text_hash="a" * 64,
    )
    strategy = ResumeStrategy(
        target_role="Senior ML Engineer",
        selected_experience_evidence_ids=(EVIDENCE_ID,),
        must_not_claim=("Kubernetes", "Go"),
    )
    budget = ResumeSpaceBudget(
        total_line_limit=47,
        header_line_limit=3,
        summary_line_limit=2,
        experience=SectionSpaceBudget(
            section="experience",
            line_limit=18,
            entry_limit=3,
            bullets_per_entry_limit=3,
        ),
        projects=SectionSpaceBudget(
            section="projects", line_limit=18, entry_limit=3, bullets_per_entry_limit=2
        ),
        skills_line_limit=4,
        education=SectionSpaceBudget(
            section="education", line_limit=2, entry_limit=1, bullets_per_entry_limit=0
        ),
    )
    record = EvidenceRecord(
        evidence_id=EVIDENCE_ID,
        source_type="experience",
        source_id="experience.titan",
        claim="Built a self-correcting resume compiler in Python.",
        skills=("Python", "Pydantic", "Jinja2"),
        confidence=1.0,
        allowed_for_resume=True,
        last_verified_at=date(2026, 8, 5),
    )
    return ResumeWritingRequest(
        job_description=jd,
        strategy=strategy,
        space_budget=budget,
        selected_evidence=(record,),
        template_id="resume_v1",
    )


# ---------------------------------------------------------------------------
# 1. Module-level version constant
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_writer_prompt_module_exposes_a_version_constant() -> None:
    """The prompt module must declare a stable, non-empty version string."""
    mod = _import_prompt_module()
    assert hasattr(mod, "PROMPT_VERSION"), "writer_v1 must define PROMPT_VERSION"
    assert isinstance(mod.PROMPT_VERSION, str)
    assert mod.PROMPT_VERSION.strip(), "PROMPT_VERSION must not be blank"


@pytest.mark.contract
def test_writer_prompt_version_matches_module_name() -> None:
    """PROMPT_VERSION should reference 'v1' to tie the constant to its module."""
    mod = _import_prompt_module()
    assert "v1" in mod.PROMPT_VERSION.lower(), "PROMPT_VERSION must contain 'v1'"


# ---------------------------------------------------------------------------
# 2. render() signature
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_writer_prompt_exposes_a_render_function() -> None:
    """render(request) must be callable and return a non-empty string."""
    mod = _import_prompt_module()
    assert callable(getattr(mod, "render", None)), "writer_v1 must expose render()"


@pytest.mark.contract
def test_writer_prompt_render_returns_a_non_empty_string() -> None:
    mod = _import_prompt_module()
    request = _build_minimal_request()
    result = mod.render(request)
    assert isinstance(result, str)
    assert result.strip(), "render() must return a non-empty string"


# ---------------------------------------------------------------------------
# 3. JSON-only output instruction
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_writer_prompt_instructs_json_only_output() -> None:
    """The prompt must explicitly require JSON output so the parser can validate."""
    mod = _import_prompt_module()
    request = _build_minimal_request()
    rendered = mod.render(request).lower()
    assert "json" in rendered, "prompt must instruct the model to return JSON"


@pytest.mark.contract
def test_writer_prompt_forbids_prose_outside_json() -> None:
    """The prompt must not permit free prose; only the JSON object is allowed."""
    mod = _import_prompt_module()
    request = _build_minimal_request()
    rendered = mod.render(request).lower()
    # Any of these phrasings satisfy the 'JSON-only' contract
    json_only_signals = [
        "only json",
        "json only",
        "no prose",
        "nothing else",
        "return only",
        "output only",
        "respond only",
        "do not include any text",
        "no other text",
    ]
    assert any(signal in rendered for signal in json_only_signals), (
        "prompt must make clear that only the JSON object is the expected output"
    )


# ---------------------------------------------------------------------------
# 4. No-LaTeX instruction
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_writer_prompt_forbids_latex_commands() -> None:
    """The prompt must explicitly prohibit LaTeX markup in any generated field."""
    mod = _import_prompt_module()
    request = _build_minimal_request()
    rendered = mod.render(request).lower()
    assert "latex" in rendered, "prompt must mention LaTeX in its prohibition"
    latex_prohibition_signals = [
        "no latex",
        "do not use latex",
        "must not contain latex",
        "latex is forbidden",
        "avoid latex",
        "without latex",
        "plain text",
    ]
    assert any(signal in rendered for signal in latex_prohibition_signals), (
        "prompt must explicitly forbid LaTeX markup"
    )


# ---------------------------------------------------------------------------
# 5. Evidence IDs injected into the rendered prompt
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_writer_prompt_includes_selected_evidence_ids() -> None:
    """Selected evidence IDs must appear in the rendered prompt text."""
    mod = _import_prompt_module()
    request = _build_minimal_request()
    rendered = mod.render(request)
    assert EVIDENCE_ID in rendered, (
        f"selected evidence ID '{EVIDENCE_ID}' must appear in the rendered prompt"
    )


@pytest.mark.contract
def test_writer_prompt_includes_evidence_claims() -> None:
    """Evidence claim text must be visible so the model can use it."""
    mod = _import_prompt_module()
    request = _build_minimal_request()
    rendered = mod.render(request)
    assert "self-correcting resume compiler" in rendered.lower(), (
        "evidence claim text must appear in the rendered prompt"
    )


# ---------------------------------------------------------------------------
# 6. Space budget injected
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_writer_prompt_includes_line_budget_totals() -> None:
    """Line limits must appear in the prompt so the model can respect them."""
    mod = _import_prompt_module()
    request = _build_minimal_request()
    rendered = mod.render(request)
    # experience line_limit=18, projects=18, total=47
    assert "18" in rendered, "experience/project line limit must appear in prompt"
    assert "47" in rendered or "total" in rendered.lower(), (
        "total line budget or 'total' label must appear in prompt"
    )


@pytest.mark.contract
def test_writer_prompt_includes_entry_and_bullet_limits() -> None:
    """Entry and bullet-per-entry ceilings must be visible in the prompt."""
    mod = _import_prompt_module()
    request = _build_minimal_request()
    rendered = mod.render(request)
    # experience: entry_limit=3, bullets_per_entry_limit=3
    assert "entry" in rendered.lower() or "entries" in rendered.lower(), (
        "entry limit must be mentioned in the prompt"
    )
    assert "bullet" in rendered.lower(), "bullet limit must be mentioned in the prompt"


# ---------------------------------------------------------------------------
# 7. must_not_claim injected
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_writer_prompt_includes_must_not_claim_terms() -> None:
    """must_not_claim terms must appear in the prompt as explicit prohibitions."""
    mod = _import_prompt_module()
    request = _build_minimal_request()
    rendered = mod.render(request)
    assert "Kubernetes" in rendered, (
        "must_not_claim term 'Kubernetes' must appear verbatim in the prompt"
    )
    assert "Go" in rendered, "must_not_claim term 'Go' must appear in the prompt"


@pytest.mark.contract
def test_writer_prompt_frames_must_not_claim_as_prohibition() -> None:
    """must_not_claim terms must be framed as prohibited, not recommended."""
    mod = _import_prompt_module()
    request = _build_minimal_request()
    rendered = mod.render(request).lower()
    prohibition_signals = [
        "must not claim",
        "do not claim",
        "must not mention",
        "do not mention",
        "forbidden",
        "prohibited",
        "must not include",
        "do not include",
    ]
    assert any(signal in rendered for signal in prohibition_signals), (
        "must_not_claim must be explicitly framed as a prohibition"
    )


# ---------------------------------------------------------------------------
# 8. Target role injected
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_writer_prompt_includes_target_role() -> None:
    """The target role must appear in the rendered prompt."""
    mod = _import_prompt_module()
    request = _build_minimal_request()
    rendered = mod.render(request)
    assert "Senior ML Engineer" in rendered, (
        "target role must appear verbatim in the rendered prompt"
    )


# ---------------------------------------------------------------------------
# 9. template_id injected
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_writer_prompt_includes_template_id() -> None:
    """The template_id must appear in the rendered prompt."""
    mod = _import_prompt_module()
    request = _build_minimal_request()
    rendered = mod.render(request)
    assert "resume_v1" in rendered, "template_id must appear in the rendered prompt"


# ---------------------------------------------------------------------------
# 10. schema_version injected
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_writer_prompt_includes_schema_version() -> None:
    """The schema_version must be visible so the model knows the response shape."""
    mod = _import_prompt_module()
    request = _build_minimal_request()
    rendered = mod.render(request)
    assert "schema_version" in rendered or "version" in rendered.lower(), (
        "schema_version or version hint must appear in the rendered prompt"
    )


@pytest.mark.contract
def test_writer_prompt_does_not_request_forbidden_schema_version_field() -> None:
    """ResumeContent accepts content_version, not request-only schema_version."""
    mod = _import_prompt_module()
    rendered = mod.render(_build_minimal_request())
    assert '"schema_version"' not in rendered
    assert "schema_version must" not in rendered.lower()
    assert '"content_version"' in rendered


# ---------------------------------------------------------------------------
# 11. Prompt stability — rendering the same request twice produces the same text
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_writer_prompt_render_is_deterministic() -> None:
    """render() must be a pure function with no randomness or timestamps."""
    mod = _import_prompt_module()
    request = _build_minimal_request()
    assert mod.render(request) == mod.render(request), (
        "render() must be deterministic for the same request"
    )


@pytest.mark.contract
def test_writer_prompt_includes_targeted_retry_feedback() -> None:
    mod = _import_prompt_module()
    request = _build_minimal_request().model_copy(
        update={"repair_feedback": ("selected_section_evidence",)}
    )

    rendered = mod.render(request)

    assert "Correction required" in rendered
    assert "selected_section_evidence" in rendered
    assert "regenerate" in rendered.lower()
