"""Provider adapters that bridge ResumeWritingRequest to a completions backend.

Architecture
------------
StructuredResumeWriter (writing.py)
    └── StructuredResumeWriterClient  [Protocol]
            ├── FakeResumeWriterAdapterClient  — deterministic test double
            └── PromptResumeWriterClient       — real adapter; uses writer_v1.render()
                    └── CompletionsBackend     [Protocol]
                            └── (any HTTP / SDK backend — injected at runtime)

The completions backend is kept behind a one-method Protocol so adapters for
OpenAI, Anthropic, Gemini, or any local model can be swapped in without
changing the writer pipeline.  API keys and credentials are never stored on
the adapter class; they are owned by the backend implementation that is
injected at startup.
"""

from dataclasses import dataclass, field
from typing import Protocol

from app.models import ResumeWritingRequest
from app.prompts import writer_v1

# ---------------------------------------------------------------------------
# CompletionsBackend — one-method Protocol for any text-generation backend
# ---------------------------------------------------------------------------


class CompletionsBackend(Protocol):
    """Minimal interface for a synchronous text-completion backend.

    Implementations are injected at runtime and may own credentials,
    HTTP sessions, rate-limit logic, or retry policies specific to a
    provider's SDK.  This boundary keeps the writer pipeline provider-neutral.
    """

    def complete(self, prompt: str) -> object:
        """Send *prompt* to the backend and return a parsed response object.

        The return type is ``object`` so the caller (PromptResumeWriterClient)
        can hand the raw result to ``ResumeContent.model_validate()`` without
        any coupling to a specific SDK's response type.
        """
        ...


# ---------------------------------------------------------------------------
# FakeResumeWriterAdapterClient — deterministic test double
# ---------------------------------------------------------------------------


@dataclass
class FakeResumeWriterAdapterClient:
    """Deterministic stand-in for a live writer adapter.

    Satisfies the StructuredResumeWriterClient protocol.  Pops from a
    pre-loaded response list and records every request so tests can assert
    on what was sent.
    """

    responses: list[object]
    requests: list[ResumeWritingRequest] = field(default_factory=list)

    def write(self, request: ResumeWritingRequest) -> object:
        """Return (or raise) the next canned response."""
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


# ---------------------------------------------------------------------------
# PromptResumeWriterClient — real provider adapter
# ---------------------------------------------------------------------------


class PromptResumeWriterClient:
    """Adapter that serializes a ResumeWritingRequest to a prompt and calls a backend.

    Satisfies the StructuredResumeWriterClient protocol.  Prompt construction
    is delegated entirely to writer_v1.render() so the prompt contract is
    testable without a live model.

    Credentials are *never* stored on this class; they belong to the backend
    implementation injected via the ``backend`` constructor argument.
    """

    def __init__(self, *, backend: CompletionsBackend) -> None:
        self._backend = backend

    def write(self, request: ResumeWritingRequest) -> object:
        """Render the prompt, call the backend, and return the raw response object.

        Does not validate the response — that is the responsibility of
        StructuredResumeWriter.  Any backend exception propagates unchanged so
        the writer's retry loop can decide how to handle it.
        """
        prompt = writer_v1.render(request)
        return self._backend.complete(prompt)
