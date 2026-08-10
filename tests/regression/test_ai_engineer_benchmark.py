import json
from pathlib import Path

import pytest

from app.services.jd import JobDescriptionIngester


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_PATH = (
    PROJECT_ROOT / "tests" / "fixtures" / "jds" / "ai_engineer_benchmark_v1.json"
)


@pytest.mark.regression
def test_ai_engineer_benchmark_covers_provenance_backed_job_sources() -> None:
    payload = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    jobs = payload["jobs"]

    assert payload["schema_version"] == 1
    assert len(jobs) >= 5
    assert {job["platform"] for job in jobs} >= {
        "google_careers",
        "indeed",
        "linkedin",
        "wellfound",
    }
    assert len({job["benchmark_id"] for job in jobs}) == len(jobs)

    ingester = JobDescriptionIngester()
    for job in jobs:
        assert job["source_url"].startswith("https://")
        assert job["captured_at"] == "2026-08-11"
        assert job["role"]
        assert job["company"]
        assert len(job["required_skills"]) >= 3
        assert ingester.ingest(job["raw_text"]).raw_text
