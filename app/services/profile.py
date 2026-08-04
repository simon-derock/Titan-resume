"""Privacy-safe access to candidate evidence records."""

import json
from collections import Counter
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from app.models import EvidenceRecord


class CandidateStoreError(ValueError):
    """Raised when private candidate evidence cannot be loaded safely."""


EVIDENCE_RECORDS_ADAPTER = TypeAdapter(tuple[EvidenceRecord, ...])


class JsonCandidateEvidenceStore:
    """Load validated candidate evidence from one local JSON document."""

    def __init__(self, store_path: Path) -> None:
        self._store_path = store_path

    def load_resume_allowed(self) -> tuple[EvidenceRecord, ...]:
        """Return only explicitly allowed records in stable identifier order."""

        records = self._load_records()
        duplicate_ids = sorted(
            evidence_id
            for evidence_id, count in Counter(
                record.evidence_id for record in records
            ).items()
            if count > 1
        )
        if duplicate_ids:
            joined_ids = ", ".join(duplicate_ids)
            raise CandidateStoreError(f"duplicate evidence IDs: {joined_ids}")

        return tuple(
            sorted(
                (record for record in records if record.allowed_for_resume),
                key=lambda record: record.evidence_id,
            )
        )

    def _load_records(self) -> tuple[EvidenceRecord, ...]:
        try:
            payload = json.loads(self._store_path.read_text(encoding="utf-8"))
        except OSError:
            raise CandidateStoreError(
                "candidate evidence store is unavailable"
            ) from None
        except json.JSONDecodeError:
            raise CandidateStoreError("candidate evidence store is malformed") from None

        try:
            return EVIDENCE_RECORDS_ADAPTER.validate_python(payload)
        except ValidationError:
            raise CandidateStoreError("candidate evidence store is malformed") from None
