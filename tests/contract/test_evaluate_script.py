import json
from pathlib import Path

import pytest

from app.graph import ResumeGraphState
from scripts.evaluate import run_evaluation


@pytest.mark.contract
def test_evaluate_script_writes_a_report_with_an_injected_executor(
    tmp_path: Path,
) -> None:
    benchmark_file = tmp_path / "benchmark.json"
    benchmark_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "captured_at": "2026-08-11",
                "description": "Public-safe test benchmark.",
                "jobs": [
                    {
                        "benchmark_id": "job.alpha",
                        "platform": "linkedin",
                        "source_url": "https://example.com/job.alpha",
                        "captured_at": "2026-08-11",
                        "role": "AI Engineer",
                        "company": "Alpha",
                        "seniority": "entry",
                        "required_skills": ["Python", "RAG", "FastAPI"],
                        "raw_text": "A production AI Engineer role. " * 4,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    header_file = tmp_path / "header.json"
    header_file.write_text(
        json.dumps({"name": "Alex Morgan", "headline": "AI Engineer"}),
        encoding="utf-8",
    )
    evidence_file = tmp_path / "evidence.json"
    evidence_file.write_text("[]", encoding="utf-8")

    class FakeExecutor:
        def run(self, **kwargs: object) -> ResumeGraphState:
            return {
                "request_id": str(kwargs["request_id"]),
                "raw_jd_text": str(kwargs["raw_jd_text"]),
                "status": "write_failed",
                "iteration": 1,
                "max_repair_cycles": 2,
                "pipeline_result": None,
                "issues": (),
                "resume_content": None,
                "repair_feedback": "fixture failure",
            }

    report_path = run_evaluation(
        benchmark_file=benchmark_file,
        evidence_file=evidence_file,
        header_file=header_file,
        output_dir=tmp_path / "artifacts",
        report_file=tmp_path / "reports" / "evaluation.json",
        template_id="deedy_cv_v1",
        model_name="gemini-3.6-flash",
        executor=FakeExecutor(),
    )

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["benchmark_count"] == 1
    assert payload["records"][0]["benchmark_id"] == "job.alpha"
    assert payload["records"][0]["status"] == "write_failed"
