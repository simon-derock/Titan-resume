"""Deterministic, evidence-grounded skill rails for asymmetric templates."""

from collections.abc import Iterable

from app.models import (
    EvidenceRecord,
    EvidenceText,
    ResumeContent,
    StructuredJobDescription,
)

_CATEGORY_ORDER = (
    ("engineering", "Engineering"),
    ("agentic_ai", "LLM & Agentic AI"),
    ("model_training_research", "Model Training & Research"),
)

_AGENTIC_MARKERS = (
    "agent",
    "rag",
    "llm",
    "langgraph",
    "langchain",
    "mcp",
    "retrieval",
    "vector",
    "semantic search",
    "embedding",
    "qdrant",
    "chroma",
    "zilliz",
    "cerebras",
    "groq",
    "mistral",
    "gemini api",
)

_RESEARCH_MARKERS = (
    "research",
    "pytorch",
    "scikit",
    "qdora",
    "qlora",
    "unsloth",
    "gguf",
    "fine-tun",
    "peft",
    "gemma",
    "multimodal",
    "ai safety",
    "predictive",
    "feature engineering",
    "data analytics",
    "opencv",
    "yolo",
    "cnn",
    "computer vision",
)

_SKILL_ROW_CHARACTER_LIMIT = 28


def build_verified_skill_rail(
    *,
    content: ResumeContent,
    evidence_records: Iterable[EvidenceRecord],
    job_description: StructuredJobDescription,
) -> ResumeContent:
    """Replace Deedy's generated skill prose with categorized verified tags."""

    if content.template_id != "deedy_cv_v1":
        return content

    records = tuple(record for record in evidence_records if record.allowed_for_resume)
    skill_support: dict[str, tuple[str, list[str]]] = {}
    for record in records:
        for skill in record.skills:
            key = skill.strip().casefold()
            if not key:
                continue
            if key not in skill_support:
                skill_support[key] = (skill.strip(), [])
            supporters = skill_support[key][1]
            if record.evidence_id not in supporters:
                supporters.append(record.evidence_id)

    if not skill_support:
        return content

    priority_terms = tuple(
        term.casefold()
        for term in (
            *job_description.must_have_skills,
            *job_description.preferred_skills,
            *job_description.keywords,
        )
        if term.strip()
    )
    grouped: dict[str, list[tuple[str, str, list[str]]]] = {
        category: [] for category, _ in _CATEGORY_ORDER
    }
    for index, (key, (display, supporters)) in enumerate(skill_support.items()):
        grouped[_skill_category(key)].append((str(index), display, supporters))

    rail: list[EvidenceText] = []
    for category, label in _CATEGORY_ORDER:
        skills = grouped[category]
        if not skills:
            continue
        ranked = sorted(
            skills,
            key=lambda item: (
                _priority_rank(item[1], priority_terms),
                int(item[0]),
            ),
        )
        evidence_ids = tuple(
            dict.fromkeys(
                evidence_id
                for _, _, supporters in ranked
                for evidence_id in supporters
            )
        )
        rail.append(
            EvidenceText(
                element_id=f"skills.{category}.heading",
                text=label,
                evidence_ids=evidence_ids,
            )
        )
        for row_index, row in enumerate(_pack_skill_rows(ranked), start=1):
            row_evidence_ids = tuple(
                dict.fromkeys(
                    evidence_id
                    for _, _, supporters in row
                    for evidence_id in supporters
                )
            )
            rail.append(
                EvidenceText(
                    element_id=f"skills.{category}.{row_index:02d}",
                    text=" | ".join(display for _, display, _ in row),
                    evidence_ids=row_evidence_ids,
                )
            )

    return content.model_copy(update={"skills": tuple(rail)})


def _skill_category(skill: str) -> str:
    if any(marker in skill for marker in _RESEARCH_MARKERS):
        return "model_training_research"
    if any(marker in skill for marker in _AGENTIC_MARKERS):
        return "agentic_ai"
    return "engineering"


def _priority_rank(skill: str, priority_terms: tuple[str, ...]) -> int:
    normalized = skill.casefold()
    return 0 if any(
        normalized == term or normalized in term or term in normalized
        for term in priority_terms
    ) else 1


def _pack_skill_rows(
    skills: list[tuple[str, str, list[str]]],
) -> tuple[tuple[tuple[str, str, list[str]], ...], ...]:
    rows: list[list[tuple[str, str, list[str]]]] = []
    current: list[tuple[str, str, list[str]]] = []
    current_length = 0
    for skill in skills:
        separator_length = 3 if current else 0
        proposed_length = current_length + separator_length + len(skill[1])
        if current and proposed_length > _SKILL_ROW_CHARACTER_LIMIT:
            rows.append(current)
            current = []
            current_length = 0
            separator_length = 0
        current.append(skill)
        current_length += separator_length + len(skill[1])
    if current:
        rows.append(current)
    return tuple(tuple(row) for row in rows)
