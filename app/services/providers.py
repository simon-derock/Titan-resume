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

import math
import re
from dataclasses import dataclass, field
from typing import Protocol

from app.models import JobDescriptionAnalysisRequest, ResumeWritingRequest
from app.prompts import jd_analyzer_v1, writer_v1

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


class FallbackCompletionsBackend:
    """Try injected completion providers in order without leaking exceptions."""

    def __init__(self, *, backends: tuple[CompletionsBackend, ...]) -> None:
        if not backends:
            raise ValueError("at least one completion backend is required")
        self._backends = backends

    def complete(self, prompt: str) -> object:
        for backend in self._backends:
            try:
                return backend.complete(prompt)
            except Exception:
                continue
        raise RuntimeError("all completion providers failed") from None


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


class PromptStructuredJdClient:
    """Serialize a typed JD analysis request for a completions backend."""

    def __init__(self, *, backend: CompletionsBackend) -> None:
        self._backend = backend

    def analyze(self, request: JobDescriptionAnalysisRequest) -> object:
        """Return the backend's raw structured response for schema validation."""

        return self._backend.complete(jd_analyzer_v1.render(request))


# ---------------------------------------------------------------------------
# GeminiCompletionsBackend — live Gemini API adapter
# ---------------------------------------------------------------------------


class GeminiCompletionsBackend:
    """Synchronous completions backend powered by Google's Gemini SDK."""

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str = "gemini-3.5-flash",
    ) -> None:

        if not api_key or not api_key.strip():
            raise ValueError("api_key must not be empty")
        self._api_key = api_key.strip()
        self._model_name = model_name

    _RETRY_STATUS_CODES: frozenset[int] = frozenset({429, 503})
    _MAX_RETRIES: int = 4
    _MAX_OUTPUT_TOKENS: int = 16_384
    _MAX_RETRY_SLEEP_SECONDS: int = 60
    _RETRY_DELAY_PATTERN = re.compile(
        r"\bretry\s+in\s+(?P<seconds>\d+(?:\.\d+)?)s\b",
        flags=re.IGNORECASE,
    )

    def complete(self, prompt: str) -> object:
        """Call Gemini API and return parsed JSON object.

        Retries up to _MAX_RETRIES times on transient 503 / 429 errors.
        Provider-supplied retry windows take precedence over the exponential
        fallback and are capped at 60 seconds per attempt.
        """
        import time

        from google import genai
        from google.genai import types
        from google.genai.errors import ClientError, ServerError

        client = genai.Client(api_key=self._api_key)

        last_exc: Exception | None = None
        for attempt in range(self._MAX_RETRIES):
            try:
                response = client.models.generate_content(
                    model=self._model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2,
                        max_output_tokens=self._MAX_OUTPUT_TOKENS,
                        candidate_count=1,
                    ),
                )
                raw_text = response.text or ""
                cleaned = self._clean_json_text(raw_text)
                return self._extract_first_json_object(cleaned)
            except (ServerError, ClientError) as exc:
                status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
                if (
                    status in self._RETRY_STATUS_CODES
                    and attempt < self._MAX_RETRIES - 1
                ):
                    wait = self._retry_delay_seconds(
                        exc,
                        fallback_seconds=2 ** (attempt + 1),
                    )
                    time.sleep(wait)
                    last_exc = exc
                    continue
                raise RuntimeError(f"Gemini API generation failed: {exc}") from exc
            except Exception as exc:
                raise RuntimeError(f"Gemini API generation failed: {exc}") from exc

        raise RuntimeError(
            "Gemini API generation failed after "
            f"{self._MAX_RETRIES} retries: {last_exc}"
        ) from last_exc

    def _retry_delay_seconds(
        self,
        exc: object,
        *,
        fallback_seconds: int,
    ) -> int:
        message = getattr(exc, "message", None)
        if not isinstance(message, str):
            return fallback_seconds

        match = self._RETRY_DELAY_PATTERN.search(message)
        if match is None:
            return fallback_seconds

        requested_seconds = math.ceil(float(match.group("seconds")))
        return min(
            max(requested_seconds, fallback_seconds),
            self._MAX_RETRY_SLEEP_SECONDS,
        )

    def _clean_json_text(self, text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return cleaned.strip()

    def _extract_first_json_object(self, text: str) -> object:
        """Parse the first complete JSON object from text, ignoring trailing garbage."""
        import json

        # Try straight parse first (fast path)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            # Walk the raw_decode path to grab only the first object
            decoder = json.JSONDecoder()
            try:
                obj, _ = decoder.raw_decode(text)
                return obj
            except json.JSONDecodeError:
                raise exc from None
