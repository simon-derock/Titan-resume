"""Run TITAN's fixed resume benchmark and persist measured JSON results."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from dotenv import load_dotenv

from app.graph import ResumeGraphExecutor, ResumeGraphState
from app.models import (
    BenchmarkCorpus,
    EvidenceRecord,
    ResumeHeader,
    ResumeTemplateId,
)
from app.services.evaluation import BenchmarkEvaluator, EvaluationReportWriter
from app.services.jd import StructuredJobDescriptionAnalyzer
from app.services.pipeline import DeterministicResumePipeline
from app.services.profile import JsonCandidateEvidenceStore
from app.services.providers import (
    GeminiCompletionsBackend,
    PromptResumeWriterClient,
    PromptStructuredJdClient,
)
from app.services.rendering import LatexCompiler
from app.services.writing import StructuredResumeWriter
from app.templates import SUPPORTED_TEMPLATE_IDS


class GraphExecutor(Protocol):
    def run(
        self,
        *,
        raw_jd_text: str,
        header: ResumeHeader,
        evidence_records: tuple[EvidenceRecord, ...],
        output_dir: Path,
        template_id: ResumeTemplateId,
        request_id: str,
    ) -> ResumeGraphState: ...


def run_evaluation(
    *,
    benchmark_file: Path,
    evidence_file: Path,
    header_file: Path,
    output_dir: Path,
    report_file: Path,
    template_id: ResumeTemplateId,
    model_name: str,
    executor: GraphExecutor | None = None,
) -> Path:
    """Execute one typed corpus and return the persisted report path."""

    corpus = BenchmarkCorpus.model_validate_json(
        benchmark_file.read_text(encoding="utf-8")
    )
    header = ResumeHeader.model_validate_json(header_file.read_text(encoding="utf-8"))
    evidence_records = JsonCandidateEvidenceStore(evidence_file).load_resume_allowed()
    active_executor = executor or _build_live_executor(model_name=model_name)
    report = BenchmarkEvaluator(executor=active_executor).run(
        corpus=corpus,
        header=header,
        evidence_records=evidence_records,
        output_root=output_dir,
        template_id=template_id,
    )
    return EvaluationReportWriter().write(report, report_file)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run TITAN's fixed resume benchmark corpus.",
    )
    parser.add_argument(
        "--benchmark-file",
        type=Path,
        default=Path("tests/fixtures/jds/ai_engineer_benchmark_v1.json"),
    )
    parser.add_argument(
        "--evidence-file",
        type=Path,
        default=Path("data/candidate_evidence.json"),
    )
    parser.add_argument("--header-file", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/evaluation/artifacts"),
    )
    parser.add_argument(
        "--report-file",
        type=Path,
        default=Path("outputs/evaluation/report.json"),
    )
    parser.add_argument(
        "--template-id",
        choices=SUPPORTED_TEMPLATE_IDS,
        default="deedy_cv_v1",
    )
    parser.add_argument("--model-name", default="gemini-3.6-flash")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report_path = run_evaluation(
        benchmark_file=args.benchmark_file,
        evidence_file=args.evidence_file,
        header_file=args.header_file,
        output_dir=args.output_dir,
        report_file=args.report_file,
        template_id=args.template_id,
        model_name=args.model_name,
    )
    print(report_path)
    return 0


def _build_live_executor(*, model_name: str) -> ResumeGraphExecutor:
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required for live evaluation")

    project_root = Path(__file__).resolve().parents[1]
    os.environ.setdefault(
        "XDG_CACHE_HOME",
        str(project_root / ".tools" / "tectonic-cache"),
    )
    backend = GeminiCompletionsBackend(api_key=api_key, model_name=model_name)
    analyzer = StructuredJobDescriptionAnalyzer(
        client=PromptStructuredJdClient(backend=backend),
        max_attempts=2,
    )
    writer = StructuredResumeWriter(
        client=PromptResumeWriterClient(backend=backend),
        max_attempts=2,
    )
    pipeline = DeterministicResumePipeline(
        compiler=LatexCompiler(
            executable=str(project_root / ".tools" / "tectonic"),
            engine="tectonic",
            timeout_seconds=120.0,
        ),
        expected_sections=("summary", "experience", "projects", "skills", "education"),
    )
    return ResumeGraphExecutor(
        writer=writer,
        pipeline=pipeline,
        jd_analyzer=analyzer,
        max_repair_cycles=2,
    )


if __name__ == "__main__":
    raise SystemExit(main())
