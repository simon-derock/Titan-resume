import json
from pathlib import Path

import pytest
from app.services.profile import CandidateStoreError, JsonCandidateEvidenceStore


def evidence_payload(
    evidence_id: str,
    *,
    allowed_for_resume: bool,
) -> dict[str, object]:
    return {
        "evidence_id": evidence_id,
        "source_type": "project",
        "source_id": "project.titan",
        "claim": f"Candidate claim for {evidence_id}",
        "skills": ["Python"],
        "metrics": {},
        "evidence_url": None,
        "confidence": 1.0,
        "allowed_for_resume": allowed_for_resume,
        "last_verified_at": "2026-08-04",
    }


def write_evidence(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(records), encoding="utf-8")


def test_candidate_store_returns_only_resume_allowed_evidence(
    tmp_path: Path,
) -> None:
    store_path = tmp_path / "evidence.json"
    write_evidence(
        store_path,
        [
            evidence_payload("evidence.zulu", allowed_for_resume=True),
            evidence_payload("evidence.private", allowed_for_resume=False),
            evidence_payload("evidence.alpha", allowed_for_resume=True),
        ],
    )

    records = JsonCandidateEvidenceStore(store_path).load_resume_allowed()

    assert tuple(record.evidence_id for record in records) == (
        "evidence.alpha",
        "evidence.zulu",
    )


def test_candidate_store_rejects_duplicate_evidence_ids(tmp_path: Path) -> None:
    store_path = tmp_path / "evidence.json"
    write_evidence(
        store_path,
        [
            evidence_payload("evidence.duplicate", allowed_for_resume=True),
            evidence_payload("evidence.duplicate", allowed_for_resume=False),
        ],
    )

    with pytest.raises(
        CandidateStoreError,
        match=r"^duplicate evidence IDs: evidence\.duplicate$",
    ):
        JsonCandidateEvidenceStore(store_path).load_resume_allowed()


@pytest.mark.parametrize(
    "contents",
    [
        "not-json",
        json.dumps({"records": []}),
        json.dumps([{"claim": "private candidate content"}]),
    ],
)
def test_candidate_store_reports_malformed_private_data_without_echoing_it(
    tmp_path: Path,
    contents: str,
) -> None:
    store_path = tmp_path / "evidence.json"
    store_path.write_text(contents, encoding="utf-8")

    with pytest.raises(CandidateStoreError) as captured:
        JsonCandidateEvidenceStore(store_path).load_resume_allowed()

    assert str(captured.value) == "candidate evidence store is malformed"
    assert "private candidate content" not in str(captured.value)


def test_candidate_store_reports_an_unavailable_private_store(tmp_path: Path) -> None:
    store_path = tmp_path / "missing.json"

    with pytest.raises(
        CandidateStoreError,
        match=r"^candidate evidence store is unavailable$",
    ):
        JsonCandidateEvidenceStore(store_path).load_resume_allowed()
