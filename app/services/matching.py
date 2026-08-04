"""Conservative deterministic matching between JD skills and evidence."""

import re
from typing import Literal

from app.models import EvidenceMatch, EvidenceRecord, StructuredJobDescription

SKILL_ALIASES = {
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    "large language model": "llm",
    "large language models": "llm",
    "machine learning": "ml",
    "postgres": "postgresql",
    "retrieval augmented generation": "rag",
}
COMPOUND_SKILL_SEPARATOR = re.compile(r"\s+(?:and|or)\s+|[/,&]")
SKILL_TOKEN = re.compile(r"[a-z0-9+#]+")
RequirementType = Literal["must_have", "preferred"]
MatchStatus = Literal["strong", "partial", "missing"]


class EvidenceMatcher:
    """Match only explicitly declared skills from resume-allowed evidence."""

    def match(
        self,
        *,
        job_description: StructuredJobDescription,
        evidence_records: tuple[EvidenceRecord, ...],
    ) -> tuple[EvidenceMatch, ...]:
        """Return stable matches for must-have requirements before preferences."""

        allowed_records = tuple(
            record for record in evidence_records if record.allowed_for_resume
        )
        requirements: tuple[tuple[RequirementType, str], ...] = (
            *(("must_have", skill) for skill in job_description.must_have_skills),
            *(("preferred", skill) for skill in job_description.preferred_skills),
        )
        return tuple(
            self._match_requirement(
                requirement_type=requirement_type,
                requirement=requirement,
                evidence_records=allowed_records,
            )
            for requirement_type, requirement in requirements
        )

    @staticmethod
    def _match_requirement(
        *,
        requirement_type: RequirementType,
        requirement: str,
        evidence_records: tuple[EvidenceRecord, ...],
    ) -> EvidenceMatch:
        components = _requirement_components(requirement)
        component_set = set(components)
        ranked_records: list[tuple[int, str]] = []
        covered_components: set[str] = set()

        for record in evidence_records:
            record_skills = {_canonical_skill(skill) for skill in record.skills}
            record_matches = component_set & record_skills
            if record_matches:
                covered_components.update(record_matches)
                ranked_records.append((len(record_matches), record.evidence_id))

        ranked_records.sort(key=lambda match: (-match[0], match[1]))
        matched_components = tuple(
            component for component in components if component in covered_components
        )
        score = len(matched_components) / len(components) if components else 0.0
        status: MatchStatus
        if score == 1.0:
            status = "strong"
        elif score > 0.0:
            status = "partial"
        else:
            status = "missing"

        return EvidenceMatch(
            requirement=requirement,
            requirement_type=requirement_type,
            status=status,
            score=score,
            matched_components=matched_components,
            evidence_ids=tuple(evidence_id for _, evidence_id in ranked_records),
        )


def _requirement_components(requirement: str) -> tuple[str, ...]:
    components = (
        _canonical_skill(part)
        for part in COMPOUND_SKILL_SEPARATOR.split(requirement.casefold())
    )
    return tuple(dict.fromkeys(component for component in components if component))


def _canonical_skill(skill: str) -> str:
    normalized = " ".join(SKILL_TOKEN.findall(skill.casefold()))
    return SKILL_ALIASES.get(normalized, normalized)
