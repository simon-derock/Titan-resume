"""Deterministic job-description ingestion boundaries."""

import hashlib
import re

from app.models import IngestedJobDescription


class JobDescriptionIngestionError(ValueError):
    """Raised when job-description source text is outside intake policy."""


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
