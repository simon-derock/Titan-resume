"""Live LLM end-to-end integration test using Gemini API across all supported templates."""

import os
from pathlib import Path
from datetime import date
import pytest

from app.models import EvidenceRecord, ResumeHeader
from app.services.providers import GeminiCompletionsBackend, PromptResumeWriterClient
from app.services.writing import StructuredResumeWriter
from app.services.pipeline import DeterministicResumePipeline
from app.services.rendering import LatexCompiler
from app.graph import ResumeGraphExecutor
from app.templates import SUPPORTED_TEMPLATE_IDS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TECTONIC_PATH = PROJECT_ROOT / ".tools" / "tectonic"
TECTONIC_CACHE_PATH = PROJECT_ROOT / ".tools" / "tectonic-cache"


@pytest.mark.live_llm
@pytest.mark.parametrize("template_id", SUPPORTED_TEMPLATE_IDS)
def test_live_gemini_writes_and_compiles_all_templates(
    tmp_path: Path, template_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY environment variable not set")

    monkeypatch.setenv("XDG_CACHE_HOME", str(TECTONIC_CACHE_PATH))

    # 1. Setup Live Backend & Writer Adapter
    # gemini-2.0-flash has a larger free-tier daily quota than gemini-3.5-flash
    backend = GeminiCompletionsBackend(api_key=api_key, model_name="gemini-2.0-flash")

    adapter = PromptResumeWriterClient(backend=backend)
    writer = StructuredResumeWriter(client=adapter, max_attempts=2)

    # 2. Setup Deterministic Resume Pipeline
    compiler = LatexCompiler(
        executable=str(TECTONIC_PATH),
        engine="tectonic",
        timeout_seconds=120.0,
    )
    pipeline = DeterministicResumePipeline(
        compiler=compiler,
        expected_sections=("summary", "experience", "projects", "skills", "education"),
    )


    # 3. Setup ResumeGraphExecutor
    executor = ResumeGraphExecutor(writer=writer, pipeline=pipeline, max_repair_cycles=2)

    # 4. Prepare inputs
    raw_jd_text = (
        "Senior AI / ML Engineer at Google DeepMind.\n"
        "Requirements:\n"
        "- Strong experience with Python, PyTorch, and LLM fine-tuning / agentic workflows.\n"
        "- Proven track record of building production AI applications with quality gates.\n"
        "- Experience with FastAPI, Jinja2, and automated evaluation pipelines."
    )
    header = ResumeHeader(
        name="Simon Derock",
        headline="Senior AI / ML Engineer",
        email="simon@example.com",
        phone="+1-555-0199",
        location="San Francisco, CA",
    )
    evidence_records = (
        EvidenceRecord(
            evidence_id="evidence.exp.titan",
            source_type="experience",
            source_id="exp.titan",
            claim="Designed and built TITAN, a self-correcting AI resume compiler in Python using Jinja2 and Tectonic.",
            skills=("Python", "Jinja2", "LaTeX", "Pydantic"),
            confidence=1.0,
            allowed_for_resume=True,
            last_verified_at=date(2026, 8, 6),
        ),
        EvidenceRecord(
            evidence_id="evidence.exp.agents",
            source_type="experience",
            source_id="exp.agents",
            claim="Engineered grounded agent workflows with PyTorch, FastAPI, and structured JSON outputs.",
            skills=("PyTorch", "FastAPI", "Python", "LLMs"),
            confidence=1.0,
            allowed_for_resume=True,
            last_verified_at=date(2026, 8, 6),
        ),
        EvidenceRecord(
            evidence_id="evidence.edu.degree",
            source_type="education",
            source_id="edu.btech",
            claim="Completed B.Tech in Artificial Intelligence & Data Science.",
            skills=("AI", "Data Science"),
            confidence=1.0,
            allowed_for_resume=True,
            last_verified_at=date(2026, 8, 6),
        ),
    )

    # 5. Run Executor
    try:
        state = executor.run(
            raw_jd_text=raw_jd_text,
            header=header,
            evidence_records=evidence_records,
            output_dir=tmp_path,
            template_id=template_id,
        )
    except RuntimeError as exc:
        err = str(exc)
        if "RESOURCE_EXHAUSTED" in err or "quota" in err.lower():
            pytest.skip(f"Gemini free-tier daily quota exhausted — try again tomorrow: {exc}")
        raise

    # 6. Assert success
    assert state["status"] == "passed", f"Execution failed for template {template_id}: {state.get('repair_feedback')}"
    assert state["pipeline_result"] is not None
    assert state["pipeline_result"].passed is True
    assert state["pipeline_result"].pdf_path is not None
    assert Path(state["pipeline_result"].pdf_path).exists()
