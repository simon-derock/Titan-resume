"""Offline orchestration for job-description and evidence intelligence."""

from app.models import EvidenceRecord, JobEvidenceIntelligenceResult
from app.services.jd import JobDescriptionIngester, StructuredJobDescriptionAnalyzer
from app.services.matching import EvidenceMatcher
from app.services.planning import SpacePlanner
from app.services.profile import JsonCandidateEvidenceStore
from app.services.strategy import ResumeStrategyBuilder


class JobEvidenceIntelligencePipeline:
    """Compose deterministic Milestone 2 services behind one typed boundary."""

    def __init__(
        self,
        *,
        ingester: JobDescriptionIngester,
        analyzer: StructuredJobDescriptionAnalyzer,
        evidence_store: JsonCandidateEvidenceStore,
    ) -> None:
        self._ingester = ingester
        self._analyzer = analyzer
        self._evidence_store = evidence_store
        self._matcher = EvidenceMatcher()
        self._space_planner = SpacePlanner()
        self._strategy_builder = ResumeStrategyBuilder()

    def run(self, raw_jd_text: str) -> JobEvidenceIntelligenceResult:
        """Build validated matches, gaps, and a bounded grounded strategy."""

        ingested_jd = self._ingester.ingest(raw_jd_text)
        job_description = self._analyzer.analyze(ingested_jd)
        evidence_records = self._evidence_store.load_resume_allowed()
        evidence_matches = self._matcher.match(
            job_description=job_description,
            evidence_records=evidence_records,
        )
        space_budget = self._space_planner.plan(
            available_experience_entries=_source_count(
                evidence_records,
                source_types={"experience", "internship"},
            ),
            available_project_entries=_source_count(
                evidence_records,
                source_types={"project"},
            ),
            available_education_entries=_source_count(
                evidence_records,
                source_types={"education", "certification"},
            ),
        )
        strategy = self._strategy_builder.build(
            job_description=job_description,
            evidence_matches=evidence_matches,
            evidence_records=evidence_records,
            space_budget=space_budget,
        )
        return JobEvidenceIntelligenceResult(
            ingested_jd=ingested_jd,
            job_description=job_description,
            evidence_matches=evidence_matches,
            space_budget=space_budget,
            strategy=strategy,
        )


def _source_count(
    evidence_records: tuple[EvidenceRecord, ...],
    *,
    source_types: set[str],
) -> int:
    return len(
        {
            record.source_id
            for record in evidence_records
            if record.source_type in source_types
        }
    )
