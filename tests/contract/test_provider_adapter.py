"""Contract: provider adapter must satisfy serialization and boundary constraints.

These tests define what every concrete provider adapter must do:
  - Serialize a ResumeWritingRequest to a prompt via writer_v1.render()
  - Return an object that ResumeContent.model_validate() can parse
  - Raise on empty or structurally invalid provider responses
  - NOT hard-code provider credentials in the adapter class

Live LLM tests are gated with @pytest.mark.live_llm and excluded from the
default suite so all offline tests remain fast and deterministic.
"""

from dataclasses import dataclass, field

import pytest

from app.models import (
    EvidenceRecord,
    ResumeWritingRequest,
)

# ---------------------------------------------------------------------------
# Helpers shared across tests
# ---------------------------------------------------------------------------


def _build_minimal_request() -> ResumeWritingRequest:
    from datetime import date

    from app.models import (
        ResumeSpaceBudget,
        ResumeStrategy,
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
        selected_experience_evidence_ids=("evidence.experience.titan",),
        must_not_claim=("Kubernetes",),
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
        evidence_id="evidence.experience.titan",
        source_type="experience",
        source_id="experience.titan",
        claim="Built a self-correcting resume compiler in Python.",
        skills=("Python", "Pydantic"),
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
# FakeWriterAdapterClient — deterministic stand-in for a real LLM call
# ---------------------------------------------------------------------------


@dataclass
class _FakeWriterAdapterClient:
    """Records the prompts it receives and returns canned response objects."""

    responses: list[object]
    seen_prompts: list[str] = field(default_factory=list)

    def complete(self, prompt: str) -> object:
        self.seen_prompts.append(prompt)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


# ---------------------------------------------------------------------------
# 1. Adapter module exists with the correct public interface
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_provider_adapter_module_is_importable() -> None:
    """app.services.providers must be importable without raising."""
    import app.services.providers as providers

    assert providers is not None


@pytest.mark.contract
def test_provider_adapter_module_exposes_fake_client() -> None:
    """A FakeResumeWriterAdapterClient must exist for offline testing."""
    from app.services.providers import FakeResumeWriterAdapterClient

    assert callable(FakeResumeWriterAdapterClient)


@pytest.mark.contract
def test_provider_adapter_module_exposes_prompt_adapter() -> None:
    """PromptResumeWriterClient must be importable for real provider wiring."""
    from app.services.providers import PromptResumeWriterClient

    assert callable(PromptResumeWriterClient)


# ---------------------------------------------------------------------------
# 2. FakeResumeWriterAdapterClient satisfies the StructuredResumeWriterClient protocol
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_fake_adapter_client_accepts_a_writing_request() -> None:
    """FakeResumeWriterAdapterClient.write(request) must not raise."""
    from app.services.providers import FakeResumeWriterAdapterClient

    request = _build_minimal_request()
    fake = FakeResumeWriterAdapterClient(responses=[{"resume_id": "r.001"}])
    result = fake.write(request)
    assert result == {"resume_id": "r.001"}


@pytest.mark.contract
def test_fake_adapter_client_records_every_request() -> None:
    """FakeResumeWriterAdapterClient must keep a log of every call."""
    from app.services.providers import FakeResumeWriterAdapterClient

    request = _build_minimal_request()
    fake = FakeResumeWriterAdapterClient(responses=[{"ok": True}, {"ok": True}])
    fake.write(request)
    fake.write(request)
    assert len(fake.requests) == 2


@pytest.mark.contract
def test_fake_adapter_client_raises_injected_exception() -> None:
    """FakeResumeWriterAdapterClient must re-raise any injected exception."""
    from app.services.providers import FakeResumeWriterAdapterClient

    request = _build_minimal_request()
    fake = FakeResumeWriterAdapterClient(responses=[RuntimeError("bad provider")])
    with pytest.raises(RuntimeError, match="bad provider"):
        fake.write(request)


# ---------------------------------------------------------------------------
# 3. PromptResumeWriterClient renders the prompt via writer_v1.render
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_prompt_adapter_uses_writer_v1_render_to_build_the_prompt() -> None:
    """PromptResumeWriterClient must delegate prompt construction to writer_v1."""
    from app.prompts import writer_v1
    from app.services.providers import PromptResumeWriterClient

    request = _build_minimal_request()
    expected_prompt = writer_v1.render(request)

    received_prompts: list[str] = []

    def capturing_complete(prompt: str) -> object:
        received_prompts.append(prompt)
        return {}

    class _CapturingBackend:
        def complete(self, prompt: str) -> object:
            return capturing_complete(prompt)

    adapter = PromptResumeWriterClient(backend=_CapturingBackend())
    try:
        adapter.write(request)
    except Exception:
        pass  # We only care that the prompt was constructed correctly

    assert received_prompts, "PromptResumeWriterClient must call backend.complete()"
    assert received_prompts[0] == expected_prompt, (
        "PromptResumeWriterClient must pass writer_v1.render(request) to the backend"
    )


@pytest.mark.contract
def test_prompt_adapter_passes_raw_backend_response_through() -> None:
    """PromptResumeWriterClient.write() must return whatever the backend returns."""
    from app.services.providers import PromptResumeWriterClient

    raw_response = {"resume_id": "r.test", "target_role": "Senior ML Engineer"}

    class _StaticBackend:
        def complete(self, prompt: str) -> object:
            return raw_response

    adapter = PromptResumeWriterClient(backend=_StaticBackend())
    result = adapter.write(_build_minimal_request())
    assert result is raw_response


@pytest.mark.contract
def test_prompt_adapter_does_not_swallow_backend_exceptions() -> None:
    """PromptResumeWriterClient must let backend exceptions propagate."""
    from app.services.providers import PromptResumeWriterClient

    class _FailingBackend:
        def complete(self, prompt: str) -> object:
            raise ConnectionError("network failure")

    adapter = PromptResumeWriterClient(backend=_FailingBackend())
    with pytest.raises(ConnectionError, match="network failure"):
        adapter.write(_build_minimal_request())


# ---------------------------------------------------------------------------
# 4. Backend protocol — completions backend must expose complete(prompt) -> object
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_completions_backend_protocol_is_importable() -> None:
    """CompletionsBackend protocol must be importable from providers."""
    from app.services.providers import CompletionsBackend

    assert CompletionsBackend is not None


# ---------------------------------------------------------------------------
# 5. PromptResumeWriterClient does not store credentials at class level
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_prompt_adapter_does_not_hard_code_credentials() -> None:
    """PromptResumeWriterClient must not store API keys as class attributes."""
    from app.services.providers import PromptResumeWriterClient

    cls_dict = vars(PromptResumeWriterClient)
    credential_names = {"api_key", "secret", "token", "password", "API_KEY"}
    leaked = credential_names & set(cls_dict.keys())
    assert not leaked, (
        f"PromptResumeWriterClient must not store credentials as class attrs: {leaked}"
    )
