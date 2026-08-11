"""Contract tests: resume graph executor state and routing boundaries.

These tests define the minimum required behaviour of the graph executor:
  - State object is serialisable (TypedDict with required keys)
  - Executor exposes a run() method returning ResumeGraphState
  - compile_failed state stops the repair loop
  - overflow or geometry failure routes to repair if iterations remain
  - max_repair_cycles is respected (hard stop)
  - Status transitions follow the defined state machine

All tests use fake/stub collaborators — no live LLM or compiler calls.
"""

import pytest

# Raw JD text used in all executor tests — must be >=80 chars for ingester
_JD_TEXT = (
    "Senior AI Engineer at TechCorp. "
    "Requirements: Python, ML, production systems, evidence grounding."
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import_graph():
    import app.graph as graph

    return graph


def _build_fake_collaborators():
    """Return stubs for every external service the executor depends on."""
    from dataclasses import dataclass, field

    from app.models import (
        CompileResult,
        DeterministicPipelineResult,
        PdfValidationReport,
    )

    @dataclass
    class FakeWriter:
        responses: list[object]
        calls: list[object] = field(default_factory=list)

        def write(self, request: object) -> object:
            self.calls.append(request)
            r = self.responses.pop(0)
            if isinstance(r, Exception):
                raise r
            return r

    @dataclass
    class FakePipeline:
        """Fake DeterministicResumePipeline for injecting compilation results."""

        results: list[DeterministicPipelineResult]

        def run(
            self,
            header: object,
            content: object,
            evidence_records: object,
            output_directory: object,
        ) -> DeterministicPipelineResult:
            r = self.results.pop(0)
            return r

    def passing_pipeline_result() -> DeterministicPipelineResult:
        return DeterministicPipelineResult(
            status="passed",
            passed=True,
            tex_path="/tmp/resume.tex",
            pdf_path="/tmp/resume.pdf",
            compile_result=CompileResult(
                success=True,
                exit_code=0,
                pdf_path="/tmp/resume.pdf",
                log="",
            ),
            page_report=PdfValidationReport(passed=True, page_count=1),
        )

    def compile_failed_result() -> DeterministicPipelineResult:
        return DeterministicPipelineResult(
            status="compile_failed",
            passed=False,
            tex_path="/tmp/resume.tex",
            compile_result=CompileResult(
                success=False,
                exit_code=1,
                pdf_path=None,
                log="LaTeX error: undefined control sequence",
                error_type="compilation_error",
            ),
        )

    def validation_failed_result() -> DeterministicPipelineResult:
        from app.models import ValidationIssue

        return DeterministicPipelineResult(
            status="validation_failed",
            passed=False,
            tex_path="/tmp/resume.tex",
            pdf_path="/tmp/resume.pdf",
            compile_result=CompileResult(
                success=True,
                exit_code=0,
                pdf_path="/tmp/resume.pdf",
                log="",
            ),
            page_report=PdfValidationReport(passed=True, page_count=1),
            issues=(
                ValidationIssue(
                    issue_id="geom.001",
                    source="geometry",
                    issue_type="unsafe_margin",
                    severity="fatal",
                    message="Left margin 10pt is below minimum 22pt",
                ),
            ),
        )

    return (
        FakeWriter,
        FakePipeline,
        passing_pipeline_result,
        compile_failed_result,
        validation_failed_result,
    )


# ---------------------------------------------------------------------------
# 1. Module-level imports
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_graph_module_is_importable() -> None:
    """app.graph must import without raising."""
    g = _import_graph()
    assert g is not None


@pytest.mark.contract
def test_graph_exposes_resume_graph_state() -> None:
    """app.graph must expose a ResumeGraphState type."""
    g = _import_graph()
    assert hasattr(g, "ResumeGraphState"), "app.graph must define ResumeGraphState"


@pytest.mark.contract
def test_graph_exposes_resume_graph_executor() -> None:
    """app.graph must expose a ResumeGraphExecutor class."""
    g = _import_graph()
    assert hasattr(g, "ResumeGraphExecutor"), (
        "app.graph must define ResumeGraphExecutor"
    )


# ---------------------------------------------------------------------------
# 2. ResumeGraphState keys
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_graph_state_has_required_keys() -> None:
    """ResumeGraphState must have the minimum required state keys."""
    g = _import_graph()
    required_keys = {
        "request_id",
        "raw_jd_text",
        "status",
        "iteration",
        "max_repair_cycles",
        "pipeline_result",
        "issues",
    }
    hints = g.ResumeGraphState.__annotations__
    missing = required_keys - set(hints.keys())
    assert not missing, f"ResumeGraphState is missing keys: {missing}"


# ---------------------------------------------------------------------------
# 3. Executor construction
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_executor_requires_writer_and_pipeline() -> None:
    """ResumeGraphExecutor must accept writer and pipeline constructor arguments."""
    g = _import_graph()
    FakeWriter, FakePipeline, passing, _, _ = _build_fake_collaborators()
    exc = g.ResumeGraphExecutor(
        writer=FakeWriter(responses=[{}]),
        pipeline=FakePipeline(results=[passing()]),
    )
    assert exc is not None


@pytest.mark.contract
def test_executor_max_repair_cycles_default_is_bounded() -> None:
    """Default max_repair_cycles must be ≥ 1 and ≤ 3 (per plan)."""
    g = _import_graph()
    FakeWriter, FakePipeline, passing, _, _ = _build_fake_collaborators()
    exc = g.ResumeGraphExecutor(
        writer=FakeWriter(responses=[{}]),
        pipeline=FakePipeline(results=[passing()]),
    )
    assert 1 <= exc.max_repair_cycles <= 3


# ---------------------------------------------------------------------------
# 4. Executor routing — happy path
# ---------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.graph
def test_executor_run_returns_passed_state_on_success(
    tmp_path,
) -> None:
    """A successful compile+validate run must set status='passed'."""
    from datetime import date

    from app.models import (
        EvidenceRecord,
        EvidenceText,
        ResumeContent,
        ResumeHeader,
    )

    g = _import_graph()
    FakeWriter, FakePipeline, passing, _, _ = _build_fake_collaborators()

    evidence_id = "evidence.experience.titan"
    valid_content = ResumeContent(
        resume_id="resume.test.001",
        target_role="AI Engineer",
        skills=(
            EvidenceText(
                element_id="skills.main",
                text="Python, Pydantic",
                evidence_ids=(evidence_id,),
            ),
        ),
        template_id="resume_v1",
    )

    header = ResumeHeader(name="Alex Morgan", headline="AI Engineer")
    writer = FakeWriter(responses=[valid_content.model_dump()])
    pipeline = FakePipeline(results=[passing()])

    exc = g.ResumeGraphExecutor(writer=writer, pipeline=pipeline)
    state = exc.run(
        raw_jd_text=_JD_TEXT,
        header=header,
        evidence_records=(
            EvidenceRecord(
                evidence_id=evidence_id,
                source_type="experience",
                source_id="experience.titan",
                claim="Built TITAN.",
                skills=("Python",),
                confidence=1.0,
                allowed_for_resume=True,
                last_verified_at=date(2026, 8, 6),
            ),
        ),
        output_dir=tmp_path,
    )

    assert state["status"] == "passed"
    assert state["iteration"] == 1
    assert state["pipeline_result"] is not None


@pytest.mark.contract
@pytest.mark.graph
def test_executor_uses_structured_jd_analysis_for_strategy_and_writer(tmp_path) -> None:
    """The graph must not reduce a rich JD to an unstructured first-line role."""
    from dataclasses import dataclass, field
    from datetime import date

    from app.models import (
        EvidenceRecord,
        EvidenceText,
        IngestedJobDescription,
        ResumeContent,
        ResumeHeader,
        StructuredJobDescription,
    )

    g = _import_graph()
    FakeWriter, FakePipeline, passing, _, _ = _build_fake_collaborators()

    evidence_id = "evidence.experience.langgraph"

    @dataclass
    class FakeJdAnalyzer:
        documents: list[IngestedJobDescription] = field(default_factory=list)

        def analyze(self, document: IngestedJobDescription) -> StructuredJobDescription:
            self.documents.append(document)
            return StructuredJobDescription(
                role="AI Software Engineer",
                company="Spiral Kite Labs",
                seniority="entry",
                must_have_skills=("LangGraph", "Python"),
                keywords=("agent workflows", "RAG"),
                raw_text_hash=document.raw_text_hash,
            )

    content = ResumeContent(
        resume_id="resume.structured-jd.001",
        target_role="AI Software Engineer",
        skills=(
            EvidenceText(
                element_id="skills.main",
                text="Python, LangGraph",
                evidence_ids=(evidence_id,),
            ),
        ),
        template_id="resume_v1",
    )
    analyzer = FakeJdAnalyzer()
    writer = FakeWriter(responses=[content.model_dump()])
    executor = g.ResumeGraphExecutor(
        writer=writer,
        pipeline=FakePipeline(results=[passing()]),
        jd_analyzer=analyzer,
    )

    state = executor.run(
        raw_jd_text=_JD_TEXT,
        header=ResumeHeader(name="Alex Morgan", headline="AI Engineer"),
        evidence_records=(
            EvidenceRecord(
                evidence_id=evidence_id,
                source_type="experience",
                source_id="experience.langgraph",
                claim="Built production LangGraph services in Python.",
                skills=("LangGraph", "Python"),
                confidence=1.0,
                allowed_for_resume=True,
                last_verified_at=date(2026, 8, 6),
            ),
        ),
        output_dir=tmp_path,
    )

    assert state["status"] == "passed"
    assert len(analyzer.documents) == 1
    request = writer.calls[0]
    assert request.job_description.role == "AI Software Engineer"
    assert request.job_description.company == "Spiral Kite Labs"
    assert request.strategy.target_role == "AI Software Engineer"
    assert request.strategy.selected_experience_evidence_ids == (evidence_id,)


# ---------------------------------------------------------------------------
# 5. Executor routing — compile failure stops immediately
# ---------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.graph
def test_executor_compile_failure_does_not_retry(tmp_path) -> None:
    """A compile failure must set status='compile_failed' without retrying."""
    from datetime import date

    from app.models import EvidenceRecord, ResumeHeader

    g = _import_graph()
    FakeWriter, FakePipeline, _, compile_failed, _ = _build_fake_collaborators()

    evidence_id = "evidence.experience.titan"

    writer = FakeWriter(
        responses=[{"resume_id": "r.001", "target_role": "AI Engineer"}]
    )
    pipeline = FakePipeline(results=[compile_failed()])

    exc = g.ResumeGraphExecutor(writer=writer, pipeline=pipeline)
    state = exc.run(
        raw_jd_text=_JD_TEXT,
        header=ResumeHeader(name="Alex Morgan", headline="AI Engineer"),
        evidence_records=(
            EvidenceRecord(
                evidence_id=evidence_id,
                source_type="experience",
                source_id="experience.titan",
                claim="Built TITAN.",
                skills=("Python",),
                confidence=1.0,
                allowed_for_resume=True,
                last_verified_at=date(2026, 8, 6),
            ),
        ),
        output_dir=tmp_path,
    )

    assert state["status"] == "compile_failed"
    # compile failure must not trigger a retry — writer was called exactly once
    assert len(writer.calls) == 1


# ---------------------------------------------------------------------------
# 6. Executor routing — validation failure triggers repair if budget remains
# ---------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.graph
def test_executor_validation_failure_triggers_repair_within_budget(
    tmp_path,
) -> None:
    """Geometry/ATS validation failure must trigger at least one repair attempt."""
    from datetime import date

    from app.models import (
        EvidenceRecord,
        EvidenceText,
        ResumeContent,
        ResumeHeader,
    )

    g = _import_graph()
    FakeWriter, FakePipeline, passing, _, validation_failed = (
        _build_fake_collaborators()
    )

    evidence_id = "evidence.experience.titan"
    valid_content = ResumeContent(
        resume_id="resume.test.002",
        target_role="AI Engineer",
        skills=(
            EvidenceText(
                element_id="skills.main",
                text="Python, Pydantic",
                evidence_ids=(evidence_id,),
            ),
        ),
        template_id="resume_v1",
    )

    writer = FakeWriter(
        responses=[
            valid_content.model_dump(),  # first attempt
            valid_content.model_dump(),  # repair attempt
        ]
    )
    pipeline = FakePipeline(
        results=[
            validation_failed(),  # first compile: geometry issue
            passing(),  # repair compile: passes
        ]
    )

    exc = g.ResumeGraphExecutor(writer=writer, pipeline=pipeline, max_repair_cycles=2)
    state = exc.run(
        raw_jd_text=_JD_TEXT,
        header=ResumeHeader(name="Alex Morgan", headline="AI Engineer"),
        evidence_records=(
            EvidenceRecord(
                evidence_id=evidence_id,
                source_type="experience",
                source_id="experience.titan",
                claim="Built TITAN.",
                skills=("Python",),
                confidence=1.0,
                allowed_for_resume=True,
                last_verified_at=date(2026, 8, 6),
            ),
        ),
        output_dir=tmp_path,
    )

    assert state["status"] == "passed"
    assert state["iteration"] == 2
    assert len(writer.calls) == 2


# ---------------------------------------------------------------------------
# 7. Executor routing — repair budget exhausted → manual_review
# ---------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.graph
def test_executor_exhausted_repair_budget_yields_manual_review(
    tmp_path,
) -> None:
    """After max_repair_cycles validation failures, status must be 'needs_review'."""
    from datetime import date

    from app.models import (
        EvidenceRecord,
        EvidenceText,
        ResumeContent,
        ResumeHeader,
    )

    g = _import_graph()
    FakeWriter, FakePipeline, _, __, validation_failed = _build_fake_collaborators()

    evidence_id = "evidence.experience.titan"
    valid_content = ResumeContent(
        resume_id="resume.test.003",
        target_role="AI Engineer",
        skills=(
            EvidenceText(
                element_id="skills.main",
                text="Python, Pydantic",
                evidence_ids=(evidence_id,),
            ),
        ),
        template_id="resume_v1",
    )

    max_cycles = 2
    writer = FakeWriter(responses=[valid_content.model_dump()] * (max_cycles + 1))
    pipeline = FakePipeline(results=[validation_failed()] * (max_cycles + 1))

    exc = g.ResumeGraphExecutor(
        writer=writer, pipeline=pipeline, max_repair_cycles=max_cycles
    )
    state = exc.run(
        raw_jd_text=_JD_TEXT,
        header=ResumeHeader(name="Alex Morgan", headline="AI Engineer"),
        evidence_records=(
            EvidenceRecord(
                evidence_id=evidence_id,
                source_type="experience",
                source_id="experience.titan",
                claim="Built TITAN.",
                skills=("Python",),
                confidence=1.0,
                allowed_for_resume=True,
                last_verified_at=date(2026, 8, 6),
            ),
        ),
        output_dir=tmp_path,
    )

    assert state["status"] == "needs_review"
    assert state["iteration"] == max_cycles + 1


# ---------------------------------------------------------------------------
# 8. Executor routing — writer failure does not crash the run
# ---------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.graph
def test_executor_writer_failure_sets_failed_status(tmp_path) -> None:
    """If the writer raises after all retries, status must be 'write_failed'."""
    from datetime import date

    from app.models import EvidenceRecord, ResumeHeader
    from app.services.writing import ResumeWritingError

    g = _import_graph()
    FakeWriter, FakePipeline, _passing, _, __ = _build_fake_collaborators()

    evidence_id = "evidence.experience.titan"

    writer = FakeWriter(responses=[ResumeWritingError(attempts=2)])
    pipeline = FakePipeline(results=[])

    exc = g.ResumeGraphExecutor(writer=writer, pipeline=pipeline)
    state = exc.run(
        raw_jd_text=_JD_TEXT,
        header=ResumeHeader(name="Alex Morgan", headline="AI Engineer"),
        evidence_records=(
            EvidenceRecord(
                evidence_id=evidence_id,
                source_type="experience",
                source_id="experience.titan",
                claim="Built TITAN.",
                skills=("Python",),
                confidence=1.0,
                allowed_for_resume=True,
                last_verified_at=date(2026, 8, 6),
            ),
        ),
        output_dir=tmp_path,
    )

    assert state["status"] == "write_failed"
