"""Version 1 of the structured resume writer prompt.

Contract requirements (enforced by tests/contract/test_writer_prompt.py):
  - PROMPT_VERSION is a non-empty string containing 'v1'.
  - render(request) is deterministic and pure.
  - The rendered text contains:
      * A JSON-only output instruction with no prose allowed.
      * An explicit LaTeX prohibition.
      * All selected evidence IDs and their claim text.
      * Line, entry, and bullet ceilings from the space budget.
      * Every must_not_claim term framed as a prohibition.
      * The target role, template_id, and schema_version.

This module NEVER calls a live model.  Prompt construction is a deterministic
function of the ResumeWritingRequest.
"""

import json

from app.models import EvidenceRecord, ResumeSpaceBudget, ResumeWritingRequest

PROMPT_VERSION: str = "writer_v1.6"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render(request: ResumeWritingRequest) -> str:
    """Return the fully rendered writer prompt for the given request.

    This function is pure and deterministic: given the same request it always
    returns the same string.  No randomness, timestamps, or external I/O.
    """
    return "\n\n".join(
        [
            _section_identity(request),
            _section_output_format(),
            _section_repair_feedback(request),
            _section_constraints(request),
            _section_space_budget(request.space_budget),
            _section_evidence(request.selected_evidence),
            _section_must_not_claim(request),
            _section_job_description(request),
            _section_response_schema(request),
        ]
    )


# ---------------------------------------------------------------------------
# Private section builders
# ---------------------------------------------------------------------------


def _section_identity(request: ResumeWritingRequest) -> str:
    return (
        f"# TITAN Structured Resume Writer — {PROMPT_VERSION}\n\n"
        f"You are a professional resume writer producing a structured JSON "
        f"resume for the role: **{request.strategy.target_role}**.\n"
        f"Template: {request.template_id}  |  "
        f"Schema version: {request.schema_version}"
    )


def _section_output_format() -> str:
    return (
        "## Output format\n\n"
        "Return ONLY a single JSON object that conforms to the schema below. "
        "Do not include any text, prose, markdown, or explanation outside the "
        "JSON object. No other text is permitted before or after the JSON.\n\n"
        "IMPORTANT: Do not use LaTeX markup anywhere in the output. "
        "All field values must be plain text only. "
        "LaTeX commands (anything matching \\command) are forbidden."
    )


def _section_repair_feedback(request: ResumeWritingRequest) -> str:
    if not request.repair_feedback:
        return "## Retry status\n\nThis is the first writing attempt."
    issues = "\n".join(f"- {issue}" for issue in request.repair_feedback)
    return (
        "## Correction required\n\n"
        "The previous JSON failed these typed validation checks:\n"
        f"{issues}\n\n"
        "Regenerate the complete JSON object and correct only these failures while "
        "preserving grounded evidence, role relevance, and all hard constraints."
    )


def _section_constraints(request: ResumeWritingRequest) -> str:
    lines = [
        "## Hard constraints",
        "",
        f"- target_role MUST be exactly: {request.strategy.target_role!r}",
        f"- template_id MUST be exactly: {request.template_id!r}",
        "- content_version MUST be exactly: 1",
        "- Every evidence_ids list must contain only the EXACT evidence_id strings "
        "listed as headings in the 'Candidate evidence' section (e.g. "
        '"evidence.exp.titan"). Do NOT use source_id or any other identifier.',
        "- Do not invent facts, metrics, or skills not present in the evidence.",
        "- An entry url MUST be copied exactly from an evidence_url referenced by "
        "that entry, or set to null when no verified URL exists.",
        "- Represent every selected experience, project, and education source in "
        "its matching section; do not omit selected sources.",
        "- Each entry and bullet evidence_ids list may contain only relevant IDs "
        "from that same section and source.",
        "- Keep bullet text at 160 characters or fewer whenever possible; the "
        "absolute schema ceiling is 205 characters including spaces.",
        "- Do not use LaTeX commands in any field value.",
        "- Return only JSON — no prose, no markdown, no other text.",
    ]
    return "\n".join(lines)


def _section_space_budget(budget: ResumeSpaceBudget) -> str:
    lines = [
        "## Space budget (hard ceilings — do not exceed)",
        "",
        f"- Total page lines: {budget.total_line_limit}",
        f"- Summary lines: {budget.summary_line_limit}",
        "- Experience:",
        f"    - Max entries: {budget.experience.entry_limit}",
        f"    - Max bullets per entry: {budget.experience.bullets_per_entry_limit}",
        f"    - Max lines for the whole section: {budget.experience.line_limit}",
        "- Projects:",
        f"    - Max entries: {budget.projects.entry_limit}",
        f"    - Max bullets per entry: {budget.projects.bullets_per_entry_limit}",
        f"    - Max lines for the whole section: {budget.projects.line_limit}",
        f"- Skills lines: {budget.skills_line_limit}",
        "- Education:",
        f"    - Max entries: {budget.education.entry_limit}",
        f"    - Max bullets per entry: {budget.education.bullets_per_entry_limit}",
        f"    - Max lines for the whole section: {budget.education.line_limit}",
        "",
        "Each bullet's target_max_lines must be ≥ 1 and ≤ 3. "
        "The sum of bullets x target_max_lines per section must not exceed the "
        "section line limit minus the entry heading lines (2 per entry).",
    ]
    return "\n".join(lines)


def _section_evidence(records: tuple[EvidenceRecord, ...]) -> str:
    lines = [
        "## Candidate evidence (only these records may be referenced)",
        "",
        "IMPORTANT: When populating evidence_ids fields in the JSON response, use the "
        "exact string shown as the heading for each evidence block below "
        '(e.g. "evidence.exp.titan"). Do NOT use source_id — use evidence_id.',
        "",
    ]
    for record in records:
        lines.append(f"### evidence_id: {record.evidence_id}")
        lines.append(f"- source_type: {record.source_type}")
        lines.append(f"- source_id: {record.source_id}")
        lines.append(f"- claim: {record.claim}")
        if record.skills:
            lines.append(f"- skills: {', '.join(record.skills)}")
        if record.metrics:
            metrics_str = json.dumps(record.metrics, separators=(",", ":"))
            lines.append(f"- metrics: {metrics_str}")
        if record.evidence_url:
            lines.append(f"- evidence_url: {record.evidence_url}")
        lines.append(f"- confidence: {record.confidence}")
        lines.append("")
    return "\n".join(lines)


def _section_must_not_claim(request: ResumeWritingRequest) -> str:
    if not request.strategy.must_not_claim:
        return (
            "## Forbidden claims\n\nNo specific terms are forbidden for this revision."
        )
    term_list = "\n".join(f"  - {term}" for term in request.strategy.must_not_claim)
    return (
        "## Forbidden claims (must not claim — prohibited)\n\n"
        "You must not claim, mention, or imply any of the following skills or "
        "technologies in any field. They are explicitly prohibited because the "
        "candidate does not have verified evidence for them:\n\n"
        f"{term_list}\n\n"
        "Violation of this prohibition will cause the entire response to be "
        "rejected and retried."
    )


def _section_job_description(request: ResumeWritingRequest) -> str:
    jd = request.job_description
    lines = [
        "## Job description context",
        "",
        f"- role: {jd.role}",
    ]
    if jd.company:
        lines.append(f"- company: {jd.company}")
    if jd.must_have_skills:
        lines.append(f"- must_have_skills: {', '.join(jd.must_have_skills)}")
    if jd.preferred_skills:
        lines.append(f"- preferred_skills: {', '.join(jd.preferred_skills)}")
    if jd.responsibilities:
        for resp in jd.responsibilities:
            lines.append(f"  - {resp}")
    if jd.keywords:
        lines.append(f"- keywords: {', '.join(jd.keywords)}")
    return "\n".join(lines)


def _section_response_schema(request: ResumeWritingRequest) -> str:
    ids_comment = '"<one or more exact relevant evidence_id values>"'
    schema = (
        "## Required JSON response schema\n\n"
        "Return exactly this JSON structure (all string values must be plain "
        "text with no LaTeX):\n\n"
        "```json\n"
        "{\n"
        f'  "resume_id": "<unique ID for this revision>",\n'
        f'  "target_role": "{request.strategy.target_role}",\n'
        f'  "template_id": "{request.template_id}",\n'
        f'  "content_version": 1,\n'
        '  "summary": {\n'
        '    "element_id": "summary.main",\n'
        '    "text": "<2-line plain-text summary>",\n'
        f'    "evidence_ids": [{ids_comment}]\n'
        "  },\n"
        '  "experience": [\n'
        "    {\n"
        '      "element_id": "<unique>",\n'
        '      "heading": "<company or role>",\n'
        '      "subheading": "<title or null>",\n'
        '      "location": "<city or null>",\n'
        '      "date_range": "<YYYY-YYYY or null>",\n'
        '      "url": "<exact verified evidence_url or null>",\n'
        f'      "evidence_ids": [{ids_comment}],\n'
        '      "bullets": [\n'
        "        {\n"
        '          "element_id": "<unique>",\n'
        '          "text": "<plain-text bullet, absolute maximum 205 characters>",\n'
        f'          "evidence_ids": [{ids_comment}],\n'
        '          "target_max_lines": 1\n'
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ],\n"
        '  "projects": [],\n'
        '  "skills": [\n'
        "    {\n"
        '      "element_id": "skills.primary",\n'
        '      "text": "<comma-separated skill groups>",\n'
        f'      "evidence_ids": [{ids_comment}]\n'
        "    }\n"
        "  ],\n"
        '  "education": []\n'
        "}\n"
        "```\n\n"
        "Return ONLY the JSON object above — no other text."
    )
    return schema
