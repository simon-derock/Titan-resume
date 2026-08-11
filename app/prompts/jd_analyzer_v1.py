"""Versioned prompt for grounded, structured job-description extraction."""

from __future__ import annotations

from app.models import JobDescriptionAnalysisRequest

PROMPT_VERSION: str = "jd_analyzer_v1.0"


def render(request: JobDescriptionAnalysisRequest) -> str:
    """Render a deterministic JSON-only extraction prompt."""

    return f"""You are TITAN's job-description analyst.

Extract only requirements explicitly supported by the supplied job description.
Do not invent, infer, or strengthen requirements that are absent from the source.
Return only JSON. Do not include markdown, prose, comments, or extra keys.

Normalization rules:
- role: the clean job title only; remove labels such as "Job Title:",
  "Position:", and "Role:".
- company: use an empty string when absent.
- seniority: exactly one of intern, entry, mid, senior, lead, principal, unspecified.
- skill and keyword arrays: concise, deduplicated strings in source order.
- use empty arrays or an empty string for information that is not stated.
- raw_text_hash: copy the exact provenance hash below.

Required response schema:
{{
  "role": "<clean job title>",
  "company": "<company or empty string>",
  "seniority": "<intern|entry|mid|senior|lead|principal|unspecified>",
  "must_have_skills": ["<explicit required skill>"],
  "preferred_skills": ["<explicit preferred skill>"],
  "responsibilities": ["<explicit responsibility>"],
  "domain": "<domain or empty string>",
  "keywords": ["<ATS keyword supported by source>"],
  "rejection_conditions": ["<explicit disqualifier>"],
  "location_constraints": ["<explicit location constraint>"],
  "experience_requirements": ["<explicit experience requirement>"],
  "raw_text_hash": "{request.raw_text_hash}"
}}

schema_version: {request.schema_version}
raw_text_hash: {request.raw_text_hash}

<job_description>
{request.raw_text}
</job_description>
"""
