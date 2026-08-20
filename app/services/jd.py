"""Deterministic job-description ingestion boundaries."""

import hashlib
import re
from collections.abc import Mapping
from typing import Protocol

from pydantic import ValidationError

from app.models import (
    IngestedJobDescription,
    JobDescriptionAnalysisRequest,
    StructuredJobDescription,
)


class JobDescriptionIngestionError(ValueError):
    """Raised when job-description source text is outside intake policy."""


class JobDescriptionAnalysisError(RuntimeError):
    """Raised after bounded structured-analysis attempts are exhausted."""

    def __init__(self, *, attempts: int, failure_codes: tuple[str, ...] = ()) -> None:
        self.attempts = attempts
        self.failure_codes = failure_codes
        super().__init__(f"structured JD analysis failed after {attempts} attempts")


class StructuredJdModelClient(Protocol):
    """Replaceable provider boundary for structured JD analysis."""

    def analyze(self, request: JobDescriptionAnalysisRequest) -> object: ...


class _ForeignSourceHashError(ValueError):
    """Internal signal for a response tied to the wrong source document."""


class StructuredJobDescriptionAnalyzer:
    """Validate bounded provider responses against canonical JD provenance."""

    def __init__(
        self,
        *,
        client: StructuredJdModelClient,
        max_attempts: int = 2,
    ) -> None:
        if not 1 <= max_attempts <= 3:
            raise ValueError("max_attempts must be between 1 and 3")
        self._client = client
        self._max_attempts = max_attempts

    def analyze(
        self,
        document: IngestedJobDescription,
    ) -> StructuredJobDescription:
        """Return schema-valid requirements or one sanitized typed failure."""

        request = JobDescriptionAnalysisRequest(
            raw_text=document.raw_text,
            raw_text_hash=document.raw_text_hash,
        )
        failure_codes: list[str] = []
        for _ in range(self._max_attempts):
            try:
                response = self._client.analyze(request)
            except Exception:
                failure_codes.append("provider_error")
                continue

            try:
                return _validate_analysis_response(
                    response,
                    expected_hash=document.raw_text_hash,
                )
            except (ValidationError, _ForeignSourceHashError):
                failure_codes.append("schema_or_source_error")
                continue

        raise JobDescriptionAnalysisError(
            attempts=self._max_attempts,
            failure_codes=tuple(dict.fromkeys(failure_codes)),
        ) from None


class JobDescriptionIngester:
    """Normalize, bound, deduplicate, and address raw job-description text."""

    def __init__(
        self,
        *,
        minimum_characters: int = 80,
        maximum_characters: int = 50_000,
    ) -> None:
        if minimum_characters < 1:
            raise ValueError("minimum_characters must be positive")
        if maximum_characters < minimum_characters:
            raise ValueError("maximum_characters must not be smaller than the minimum")
        self._minimum_characters = minimum_characters
        self._maximum_characters = maximum_characters

    def ingest(self, raw_text: str) -> IngestedJobDescription:
        """Return normalized source text with a stable SHA-256 content hash."""

        if len(raw_text) > self._maximum_characters:
            raise JobDescriptionIngestionError("job description exceeds the size limit")

        normalized_text = _normalize_job_description(raw_text)
        if len(normalized_text) < self._minimum_characters:
            raise JobDescriptionIngestionError("job description is too short")

        content_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
        return IngestedJobDescription(
            raw_text=normalized_text,
            raw_text_hash=content_hash,
        )


def _normalize_job_description(raw_text: str) -> str:
    normalized_newlines = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    raw_blocks = re.split(r"\n\s*\n+", normalized_newlines)
    unique_blocks: list[str] = []
    seen_blocks: set[str] = set()

    for raw_block in raw_blocks:
        lines = tuple(
            normalized_line
            for line in raw_block.splitlines()
            if (normalized_line := re.sub(r"\s+", " ", line).strip())
        )
        block = "\n".join(lines)
        if block and block not in seen_blocks:
            seen_blocks.add(block)
            unique_blocks.append(block)

    return "\n\n".join(unique_blocks)


def _validate_analysis_response(
    response: object,
    *,
    expected_hash: str,
) -> StructuredJobDescription:
    if isinstance(response, Mapping):
        payload = dict(response)
        response_hash = payload.get("raw_text_hash")
        if response_hash is not None and response_hash != expected_hash:
            raise _ForeignSourceHashError
        payload["raw_text_hash"] = expected_hash
        return StructuredJobDescription.model_validate(payload)

    result = StructuredJobDescription.model_validate(response)
    if result.raw_text_hash != expected_hash:
        raise _ForeignSourceHashError
    return result
