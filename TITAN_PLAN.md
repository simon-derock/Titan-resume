# PLAN.md — TITAN: Self-Correcting AI Resume Compiler

> **Final name:** **TITAN**
> **Full title:** **TITAN — SELF-CORRECTING AI RESUME COMPILER**  
> **Product type:** Lightweight, evidence-grounded, multimodal resume optimization agent  
> **Primary interface:** Telegram bot  
> **Core orchestration:** LangGraph  
> **Document engine:** Structured JSON → locked LaTeX template → PDF  
> **Hard output constraint:** Every generated resume must be exactly one page

---

## 1. Product Persona

You are a **Senior AI Systems Engineer, Resume Strategist, and Document-Quality Architect** building a production-grade agentic system.

You think and work like:

- A senior AI engineer designing reliable LangGraph workflows
- A professional technical-resume writer
- An ATS-aware recruiter reviewing AI Engineer applications
- A document-layout engineer who validates the rendered PDF
- A strict test-driven developer who never writes untested production behavior
- A reliability engineer who prefers deterministic validation over vague LLM judgment
- A privacy-conscious engineer handling sensitive candidate information

The system itself behaves as:

> An evidence-grounded resume compiler that understands a job description, retrieves verified candidate evidence, writes space-aware content, compiles a one-page LaTeX resume, visually inspects the final PDF, measures its geometry, and applies bounded element-level repairs until all quality gates pass.

---

## 2. End Goal

Build a lightweight Telegram-controlled agent that:

1. Stores the candidate’s complete, updateable career knowledge:
   - Base resume
   - LinkedIn information
   - Work experience
   - Internships
   - Projects
   - Skills
   - Achievements
   - Metrics
   - GitHub repositories
   - Portfolio links
   - Education
   - Certifications
   - Evidence and provenance for every claim

2. Receives a job description through:
   - Telegram text
   - Telegram document
   - Screenshot
   - PDF
   - Job-posting URL in a later version

3. Converts the JD into structured requirements.

4. Matches each requirement against verified candidate evidence.

5. Chooses the best truthful positioning for that role.

6. Writes a tailored resume under a physical one-page space budget.

7. Compiles the resume through a locked, reliable LaTeX template.

8. Validates:
   - Exactly one page
   - ATS-readable text
   - Correct text order
   - No unsupported claims
   - Safe margins
   - Minimum readable font size
   - Consistent alignment
   - Strong JD coverage
   - Good visual balance

9. Uses a vision-capable model to inspect the full rendered resume like a human recruiter and document designer.

10. Applies only targeted edits to the affected bullet, section, or layout token.

11. Recompiles through a bounded LangGraph loop.

12. Sends the final PDF, screenshot, score report, and approval controls through Telegram.

---

## 3. Product Positioning

Do not position this as a generic “AI resume builder.”

### Final identity

- **Codename:** `TITAN`
- **Display name:** **TITAN — SELF-CORRECTING AI RESUME COMPILER**
- **GitHub repository:** `titan-resume`
- **Hugging Face Space:** `titan-resume-agent`
- **Python package:** `titan_resume`
- **Docker image:** `titan-resume`
- **Telegram bot:** `Titan Resume Bot`

Use **TITAN** in product-facing headings and `titan-resume` for repository,
container, deployment, and artifact identifiers.

### Product statement

> A vision-guided, evidence-grounded, one-page resume compiler that sees and repairs the final rendered PDF.

### Technical positioning

> A LangGraph-orchestrated document optimization system combining career-memory retrieval, claim provenance, LaTeX compilation, PDF geometry analysis, multimodal layout evaluation, deterministic quality gates, and bounded self-correction.

### Portfolio value

The project must visibly demonstrate:

- LangGraph cyclic workflows
- Typed shared state
- Conditional routing
- Human-in-the-loop approval
- Structured LLM outputs
- Tool calling
- Multimodal reasoning
- Document intelligence
- Retrieval and evidence grounding
- Anti-hallucination controls
- Deterministic validators
- Failure recovery
- Checkpointing
- Evaluation-driven engineering
- Telegram integration
- Production-oriented API design
- Pure test-driven development

---

## 4. USP and Defensible Moat

### USP

The system does not stop after writing text or exporting a PDF.

It performs:

```text
Understand JD
→ retrieve verified evidence
→ plan page content
→ write constrained resume
→ compile LaTeX
→ inspect final page
→ measure geometry
→ diagnose defects
→ patch exact elements
→ recompile
→ approve
```

### Long-term moat

The moat will not be the use of LangGraph, LaTeX, Telegram, or a vision API. Those are reproducible.

The defensible assets are:

1. **Resume defect dataset**
   - Rendered page
   - Detected defect
   - Exact element ID
   - Human-approved repair
   - Before/after measurements

2. **Compiler-aware repair policy**
   - Maps each layout defect to the safest repair action

3. **Claim provenance graph**
   - Every resume phrase traces back to verified evidence

4. **Application-outcome dataset**
   - JD
   - Resume version
   - ATS score
   - Visual score
   - Recruiter response
   - Interview outcome

5. **Evaluation suite**
   - Repeatable benchmark JDs
   - Golden candidate profile
   - Golden PDFs
   - Human-labelled layout issues

---

## 5. Hard Product Constraints

These rules are non-negotiable.

### Resume constraints

- Output must be exactly one page.
- Traditional header and footer reservations must be disabled.
- Margins must be compact but safe.
- No text may touch or cross page boundaries.
- Body font may never fall below the configured minimum.
- ATS text extraction must succeed.
- Reading order must remain logical.
- Unsupported claims are forbidden.
- The system may not fabricate metrics, employers, dates, tools, or outcomes.
- Every generated claim must include one or more evidence IDs.
- The final resume should use the page efficiently without appearing compressed.
- The master knowledge store may contain everything; the final resume must contain only the strongest role-relevant subset.

### Engineering constraints

- Pure TDD.
- No production behavior without a failing test first.
- All LLM outputs must be validated by Pydantic schemas.
- LLM-generated raw LaTeX is forbidden.
- Templates are locked and versioned.
- Repair loops are bounded.
- A deterministic validator can veto an LLM decision.
- Vision output is advisory until confirmed by geometry or policy.
- External model calls must be replaceable with mocks.
- The system must work locally with minimal infrastructure.
 - Version 1 supports three production templates: `resume_v1` (single-column
   A4), `moderncv_two_column_v1` (two-column banking-style A4, production
   adaptation uses stable article primitives — see compiler decision below),
   and `deedy_cv_v1` (two-column A4, Apache-2.0). Reference sources are
   retained under `latex_templates/` for attribution only.
- Initial version uses SQLite or JSON; no vector database unless retrieval quality proves it necessary.
- One orchestration service; no premature microservices.

---

## 6. Scope

### Version 1 — Must have

- Private Telegram bot with admin allowlist
- JD text ingestion
- Structured JD parser
- Candidate knowledge store
- Requirement-to-evidence matcher
- Resume strategy generator
- Space budget planner
- Structured resume writer
 - Three locked LaTeX templates:
   - `resume_v1.tex.j2` — single-column A4, TITAN ATS style
   - `moderncv_two_column_v1.tex.j2` — two-column banking-inspired A4
     (production adaptation uses stable `article` primitives; original
     `moderncv.cls` causes a `free(): invalid pointer` crash in Tectonic
     0.16.9 via its FontAwesome dependency; reference source retained in
     `latex_templates/` for design provenance)
   - `deedy_cv_v1.tex.j2` — two-column A4, Apache-2.0 (Deedy Resume by
     Debarghya Das; reference source in `latex_templates/`)
- PDF compilation
- One-page validator
- PDF text extraction
- Geometry checks
- Full-page screenshot rendering
- Vision-layout critic
- Targeted repair loop
- Human approval
- Final PDF delivery
- Complete test suite
- Evaluation report

### Version 1 — Explicit non-goals

- Public multi-user SaaS
- Billing
- Dozens of templates
- Full web frontend
- Kubernetes
- Separate services for every agent
- Fully autonomous job applications
- Unbounded self-improvement
- Automatic invention of missing information
- Pixel-perfect graphic-design resumes
- Supporting every document format at launch

### Later versions

 - Additional community templates beyond the current three
- URL ingestion
- OCR-based screenshot parsing
- LinkedIn import
- GitHub project evidence ingestion
- Portfolio parsing
- Embedding retrieval
- Application tracking
- Outcome learning
- Generalized one-page document optimization

---

## 7. Compact Repository Structure

Keep the repository easy to understand.

```text
titan-resume/
├── app/
│   ├── api.py
│   ├── bot.py
│   ├── graph.py
│   ├── models.py
│   ├── config.py
│   └── services/
│       ├── jd.py
│       ├── profile.py
│       ├── matching.py
│       ├── writing.py
│       ├── rendering.py
│       ├── validation.py
│       ├── vision.py
│       └── storage.py
├── templates/
│   ├── resume_v1.tex.j2
│   ├── moderncv_two_column_v1.tex.j2
│   ├── deedy_cv_v1.tex.j2
│   └── template_config.yaml
├── latex_templates/
│   └── (reference sources for design provenance and attribution)
├── data/
│   ├── candidate_profile.json
│   ├── evidence.json
│   └── fixtures/
├── prompts/
│   ├── jd_analyzer.md
│   ├── strategist.md
│   ├── writer.md
│   ├── vision_critic.md
│   └── repairer.md
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   ├── regression/
│   └── fixtures/
├── scripts/
│   ├── compile_resume.py
│   ├── render_page.py
│   └── evaluate.py
├── outputs/
├── PLAN.md
├── memory.md
├── README.md
├── pyproject.toml
├── .env.example
└── Makefile
```

Do not create extra folders without a concrete need.

---

## 8. Core Data Model

### 8.1 Candidate profile

The candidate profile stores stable identity and career information.

```json
{
  "candidate_id": "philip_simon_derock",
  "identity": {
    "name": "Philip Simon Derock",
    "headline": "AI Engineer",
    "location": "Tamil Nadu, India"
  },
  "contact": {
    "email": "",
    "phone": "",
    "linkedin": "",
    "github": "",
    "portfolio": ""
  },
  "education": [],
  "experience": [],
  "internships": [],
  "projects": [],
  "skills": [],
  "achievements": [],
  "preferences": {
    "target_roles": ["AI Engineer", "Agent Engineer", "LLM Engineer"],
    "page_count": 1
  }
}
```

### 8.2 Evidence record

Every usable resume claim must originate from an evidence record.

```json
{
  "evidence_id": "blackcoat_langgraph_001",
  "source_type": "experience",
  "source_id": "blackcoat_ai",
  "claim": "Built a LangGraph-based legal Agentic RAG workflow.",
  "skills": ["LangGraph", "Agentic RAG", "FastAPI"],
  "metrics": {
    "acts": 56,
    "sections": 5569
  },
  "evidence_url": null,
  "confidence": 1.0,
  "allowed_for_resume": true,
  "last_verified_at": "YYYY-MM-DD"
}
```

### 8.3 Structured JD

```json
{
  "role": "AI Engineer",
  "company": "Example",
  "seniority": "mid",
  "must_have_skills": [],
  "preferred_skills": [],
  "responsibilities": [],
  "domain": "",
  "keywords": [],
  "rejection_conditions": [],
  "location_constraints": [],
  "experience_requirements": [],
  "raw_text_hash": ""
}
```

### 8.4 Resume content

```json
{
  "resume_id": "",
  "target_role": "",
  "summary": {
    "text": "",
    "evidence_ids": []
  },
  "experience": [],
  "projects": [],
  "skills": [],
  "education": [],
  "template_id": "resume_v1",
  "content_version": 1
}
```

Every bullet must have:

```json
{
  "element_id": "experience.blackcoat.bullet_1",
  "text": "",
  "evidence_ids": [],
  "priority": 0.0,
  "target_max_lines": 3,
  "protected_terms": []
}
```

### 8.5 Validation issue

```json
{
  "issue_id": "",
  "source": "geometry|vision|ats|provenance|compiler",
  "element_id": "",
  "issue_type": "",
  "severity": "low|medium|high|fatal",
  "message": "",
  "recommended_action": "",
  "measured_value": null,
  "expected_value": null
}
```

---

## 9. LangGraph State

Use one typed state object.

```python
class ResumeGraphState(TypedDict):
    request_id: str
    user_id: str

    raw_jd_text: str
    structured_jd: dict

    candidate_profile: dict
    retrieved_evidence: list[dict]
    evidence_matches: list[dict]

    resume_strategy: dict
    space_budget: dict
    resume_content: dict

    template_id: str
    tex_path: str | None
    pdf_path: str | None
    screenshot_path: str | None

    compile_result: dict
    deterministic_report: dict
    vision_report: dict
    validation_issues: list[dict]

    iteration: int
    max_iterations: int
    status: str
    user_feedback: str | None
    approved: bool
```

State must be serializable and checkpointable.

---

## 10. LangGraph Nodes

### 10.1 `ingest_jd`

Responsibilities:

- Accept JD text
- Normalize whitespace
- Remove obvious duplicated blocks
- Calculate a content hash
- Reject empty or extremely short input

Output:

- `raw_jd_text`

### 10.2 `analyze_jd`

Responsibilities:

- Extract role, seniority, skills, responsibilities, domain, constraints, and priorities
- Return validated structured JSON
- Preserve explicit wording from the JD where useful

Output:

- `structured_jd`

### 10.3 `load_candidate_profile`

Responsibilities:

- Load candidate profile
- Load verified evidence records
- Reject malformed or unverified records

Output:

- `candidate_profile`

### 10.4 `match_evidence`

Responsibilities:

- Match JD requirements to evidence
- Score relevance
- Separate:
  - Strong matches
  - Partial matches
  - Missing requirements
- Never treat an unproven skill as evidence

Output:

- `retrieved_evidence`
- `evidence_matches`

### 10.5 `build_strategy`

Responsibilities:

- Decide the candidate positioning
- Rank experience and projects
- Select role-relevant skills
- Identify the most important JD language
- Define what must be omitted
- Define what must not be claimed

Output:

- `resume_strategy`

### 10.6 `plan_space`

Responsibilities:

- Allocate expected lines to each section
- Reserve space before writing
- Determine maximum entries and bullets
- Prevent uncontrolled content generation

Suggested initial budget:

```yaml
header: 2-3 lines
summary: 2 lines
experience: 16-20 lines
projects: 18-24 lines
skills: 3-5 lines
education: 1-2 lines
```

Output:

- `space_budget`

### 10.7 `write_resume`

Responsibilities:

- Generate structured resume content
- Use only supplied evidence IDs
- Respect line and section limits
- Prefer action + system + technical mechanism + result
- Keep important JD terms
- Avoid keyword dumping
- Never generate LaTeX

Output:

- `resume_content`

### 10.8 `render_latex`

Responsibilities:

- Validate resume JSON
- Insert content into a locked Jinja2 LaTeX template
- Escape unsafe LaTeX characters
- Create deterministic element markers where possible
- Generate `.tex`

Output:

- `tex_path`

### 10.9 `compile_pdf`

Responsibilities:

- Compile inside a restricted subprocess
- Capture logs
- Enforce timeout
- Reject shell escape
- Return page count and compilation errors

Output:

- `pdf_path`
- `compile_result`

### 10.10 `validate_deterministically`

Responsibilities:

- Verify page count equals one
- Extract PDF text
- Verify reading order
- Verify minimum font size
- Inspect bounding boxes
- Measure margins
- Measure date and heading alignment
- Detect clipping and overlap
- Validate links
- Validate evidence provenance
- Calculate JD requirement coverage

Output:

- `deterministic_report`
- `validation_issues`

### 10.11 `render_screenshot`

Responsibilities:

- Render the complete first page at high resolution
- Preserve exact page ratio
- Store image for vision review and Telegram preview

Output:

- `screenshot_path`

### 10.12 `vision_review`

Responsibilities:

Review as:

1. AI engineering recruiter
2. Professional resume writer
3. Document-layout reviewer
4. ATS-aware reviewer

Inspect:

- First-impression scanability
- Visual hierarchy
- Density
- Uneven whitespace
- Excessive wrapping
- Weak alignment
- Inconsistent spacing
- Crowded skills
- Poor project prioritization
- Unprofessional visual patterns

The vision model must output structured issues with exact element IDs where available.

Output:

- `vision_report`
- additional `validation_issues`

### 10.13 `decide_next_action`

Deterministic router.

Routes:

```text
compile failure
→ repair_rendering

page count > 1
→ compress_content

unsupported claim
→ repair_claim

fatal geometry issue
→ repair_layout

visual issue
→ targeted_rewrite

all gates passed
→ request_approval

max iterations reached
→ request_manual_review
```

### 10.14 `targeted_repair`

Responsibilities:

- Receive only the affected elements
- Preserve protected terms and evidence
- Apply one minimal repair
- Never regenerate unrelated sections
- Increment content version

Output:

- patched `resume_content`

### 10.15 `request_approval`

Responsibilities:

Send through Telegram:

- PDF
- Full-page screenshot
- Target role and company
- JD coverage score
- Visual score
- One-page status
- Repair count
- Warnings
- Approve/regenerate/edit actions

### 10.16 `apply_user_feedback`

Responsibilities:

- Parse explicit user instruction
- Update only requested fields
- Return to rendering and validation
- Preserve history

---

## 11. Graph Flow

```text
START
  ↓
ingest_jd
  ↓
analyze_jd
  ↓
load_candidate_profile
  ↓
match_evidence
  ↓
build_strategy
  ↓
plan_space
  ↓
write_resume
  ↓
render_latex
  ↓
compile_pdf
  ↓
validate_deterministically
  ↓
render_screenshot
  ↓
vision_review
  ↓
decide_next_action
  ├── pass ───────────────→ request_approval
  ├── compile failure ────→ repair_rendering
  ├── overflow ───────────→ targeted_repair
  ├── visual defect ──────→ targeted_repair
  ├── unsupported claim ──→ targeted_repair
  └── max iterations ─────→ request_manual_review

targeted_repair
  ↓
render_latex
```

The loop must default to a maximum of three automated repairs.

---

## 12. Page Layout Policy

### Initial LaTeX configuration

Recommended safe starting bounds:

```yaml
page_size: A4
page_count: 1
top_margin_in: 0.30
bottom_margin_in: 0.30
left_margin_in: 0.38
right_margin_in: 0.38
header_enabled: false
footer_enabled: false
minimum_body_font_pt: 9.3
target_page_fill_percent: 93-98
```

### Layout rules

- Use a full-width, single-column structure initially.
- Avoid a permanent sidebar.
- Keep dates right-aligned consistently.
- Use compact section spacing.
- Skills should be grouped into compact, role-relevant lines.
- Experience and project evidence receive priority over long keyword lists.
- Font reduction is the last repair action.
- Margin reduction below configured safety limits is forbidden.
- The system must not solve overflow by shrinking the entire document immediately.

### Repair priority

When content overflows:

1. Remove irrelevant words
2. Remove repeated technologies
3. Shorten the lowest-priority bullet
4. Merge related information
5. Remove the lowest-priority bullet
6. Remove the weakest project or internship
7. Slightly reduce safe spacing
8. Slightly adjust safe margins
9. Reduce body font only within approved bounds

When the page is underfilled:

1. Restore a high-value omitted bullet
2. Add a verified metric
3. Add an important JD-relevant project
4. Improve section spacing
5. Slightly increase readability
6. Never insert filler

---

## 13. Vision Review Contract

The vision model must not receive an open-ended prompt such as “Is this resume good?”

It receives:

- Full-page screenshot
- Resume element map
- Template specification
- Space constraints
- JD summary
- Deterministic measurements

Required response:

```json
{
  "overall_score": 8.7,
  "scanability_score": 9.0,
  "alignment_score": 9.4,
  "density_score": 7.8,
  "hierarchy_score": 8.9,
  "issues": [
    {
      "element_id": "projects.dex_jobs.bullet_2",
      "issue_type": "excessive_wrapping",
      "severity": "high",
      "observation": "The bullet creates a dense five-line block.",
      "target_change": "Reduce by approximately 15 words.",
      "preserve": [
        "custom ReAct loop",
        "multi-provider routing"
      ]
    }
  ]
}
```

### Vision limitations

- Vision is not trusted for exact measurements.
- Geometry tools determine coordinates and font sizes.
- Vision finds perceptual defects.
- Geometry confirms structural defects.
- A combined policy decides repairs.

---

## 14. Deterministic Validation Rules

A resume passes only when:

```yaml
compile_success: true
page_count: 1
text_extractable: true
reading_order_valid: true
unsupported_claim_count: 0
fatal_geometry_issue_count: 0
minimum_font_size_passed: true
margin_safety_passed: true
jd_must_have_coverage: ">= configured threshold"
iteration_count: "<= max_iterations"
```

Suggested geometry checks:

```yaml
heading_x_tolerance_pt: 2
date_right_edge_tolerance_pt: 3
bullet_indent_tolerance_pt: 2
minimum_bottom_margin_pt: 20
minimum_top_margin_pt: 18
minimum_horizontal_margin_pt: 22
maximum_bullet_lines: 3
```

These values must be calibrated through tests and real PDFs.

---

## 15. Pure Test-Driven Development Policy

### Absolute rule

> No production code is written until a failing automated test describes the intended behavior.

Every change follows:

```text
RED
→ write the smallest failing test

GREEN
→ write the smallest implementation that passes

REFACTOR
→ improve structure without changing behavior

VERIFY
→ run the full affected suite

DOCUMENT
→ update memory.md
```

### Prohibited workflow

```text
Write implementation
→ manually test
→ add tests later
```

This is forbidden.

### Test naming

Tests must describe behavior:

```python
def test_compile_validator_rejects_two_page_pdf():
    ...

def test_writer_cannot_use_claim_without_evidence_id():
    ...

def test_repairer_modifies_only_flagged_element():
    ...
```

Avoid vague names such as:

```python
def test_resume():
    ...
```

---

## 16. Testing Strategy

### 16.1 Unit tests

Fast, isolated, no real network calls.

Test:

- JD normalization
- Skill extraction helpers
- Evidence scoring
- Space budgeting
- LaTeX escaping
- Template rendering
- Page count parsing
- Geometry calculations
- Provenance validation
- Repair policy routing
- Telegram authorization
- Configuration validation

### 16.2 Contract tests

Validate every LLM node against strict schemas.

Test:

- Valid output parses
- Missing required fields fail
- Extra unsupported claims fail
- Unknown evidence IDs fail
- Invalid element IDs fail
- Invalid severity labels fail
- Unbounded suggestions fail

Use stored fixture responses. Do not call a live model in normal CI.

### 16.3 Integration tests

Test complete module chains:

- JD → structured JD
- Structured JD → evidence matches
- Resume JSON → LaTeX
- LaTeX → one-page PDF
- PDF → geometry report
- Validation issue → targeted repair
- Telegram request → graph invocation

### 16.4 Graph tests

Test node transitions and conditional edges.

Required cases:

- Successful first-pass resume
- Compile failure
- Two-page overflow
- Unsupported claim
- Visual defect
- Maximum iteration reached
- Human rejection
- Human edit request
- Checkpoint resume after interruption

### 16.5 Regression tests

Maintain golden fixtures for:

- Candidate profile
- Representative JDs
- Resume JSON
- `.tex`
- PDF text extraction
- Geometry report
- Vision-response fixtures
- Final quality report

Do not require byte-identical PDFs across all operating systems. Compare:

- Page count
- Text content
- Bounding-box tolerances
- Font ranges
- Section positions
- Issue counts

### 16.6 Visual tests

Use curated screenshots with known defects:

- Excessive bottom whitespace
- Text touching margins
- Misaligned dates
- Long wrapped bullet
- Dense skills block
- Weak hierarchy
- Uneven section spacing
- Two-page overflow
- Clipped links
- Tiny body font

Vision tests should be split into:

1. Offline contract tests using stored model responses
2. Optional live evaluation tests excluded from default CI

### 16.7 Security tests

Test:

- Unauthorized Telegram user rejected
- LaTeX injection escaped
- Shell escape disabled
- Compiler timeout enforced
- Malformed file rejected
- Oversized JD rejected
- Prompt injection inside JD cannot override system constraints
- Candidate evidence cannot be leaked to unauthorized users

---

## 17. First Tests to Write

Implement in this exact order.

### Test 1 — configuration

```python
def test_settings_require_admin_telegram_id():
    ...
```

### Test 2 — one-page invariant

```python
def test_resume_policy_requires_exactly_one_page():
    ...
```

### Test 3 — evidence grounding

```python
def test_resume_bullet_requires_existing_evidence_id():
    ...
```

### Test 4 — structured JD schema

```python
def test_structured_jd_rejects_missing_role():
    ...
```

### Test 5 — candidate store

```python
def test_candidate_store_returns_only_resume_allowed_evidence():
    ...
```

### Test 6 — space planner

```python
def test_space_budget_never_allocates_unbounded_bullets():
    ...
```

### Test 7 — safe renderer

```python
def test_renderer_escapes_latex_special_characters():
    ...
```

### Test 8 — compile tool

```python
def test_compiler_returns_structured_failure_on_invalid_tex():
    ...
```

### Test 9 — page validator

```python
def test_page_validator_rejects_two_page_pdf():
    ...
```

### Test 10 — targeted repair

```python
def test_targeted_repair_cannot_modify_unflagged_elements():
    ...
```

### Test 11 — graph routing

```python
def test_graph_routes_overflow_to_targeted_repair():
    ...
```

### Test 12 — approval

```python
def test_final_resume_is_not_delivered_before_all_gates_pass():
    ...
```

---

## 18. Mocking LLMs

Production logic must not depend on live model availability during development.

Create an interface:

```python
class LLMClient(Protocol):
    async def generate_structured(
        self,
        prompt_name: str,
        payload: dict,
        response_model: type[BaseModel],
    ) -> BaseModel:
        ...
```

Implement:

- `FakeLLMClient`
- `RecordedLLMClient`
- `ProductionLLMClient`

Tests use `FakeLLMClient`.

Live calls are allowed only in:

- Manual evaluation
- Explicit live integration suite
- Production execution

---

## 19. Prompt Architecture

Do not create three full agents merely because three templates may exist.

Use small role-specific prompt modules:

- JD analyzer
- Resume strategist
- Resume writer
- Vision critic
- Targeted repairer

Each prompt receives only the context required for its node.

### Prompt rules

- No hidden candidate facts
- No unrestricted access to the entire database
- No raw LaTeX editing
- No unsupported claims
- No changing template geometry unless explicitly authorized
- Return JSON only
- Cite evidence IDs
- Preserve protected JD terms
- State uncertainty rather than invent information

Prompt versions must be recorded in evaluation output.

---

## 20. Candidate Knowledge Store

### Initial implementation

Use:

- JSON files for seed data
- SQLite for indexed runtime storage
- Pydantic for validation

A vector database is not required initially because the profile size is small.

Use deterministic retrieval first:

- Exact skill tags
- Aliases
- Role tags
- Domain tags
- Evidence confidence
- Project priority
- Recency
- Verified metrics

Add embeddings only when benchmarks prove deterministic matching is insufficient.

### Skill aliases

Example:

```json
{
  "LangGraph": ["lang graph", "graph-based agent orchestration"],
  "MCP": ["model context protocol", "FastMCP"],
  "RAG": ["retrieval augmented generation", "agentic rag", "hybrid rag"]
}
```

---

## 21. Telegram Flow

### Access control

- Bot token in environment variables
- Admin user IDs in environment variables or secure config
- Reject every non-allowlisted user
- Prefer a private bot chat for version 1
- A private group can be supported later

### Commands

```text
/start
/profile
/add_evidence
/update_skill
/new_resume
/status
/approve
/reject
/edit
/history
```

### Generation flow

```text
User sends JD
→ bot confirms detected role/company
→ graph generates resume
→ bot sends screenshot + quality report
→ bot sends PDF
→ user approves or requests targeted edit
```

### Approval controls

- Approve
- Rewrite summary
- Replace project
- Emphasize skill
- Remove skill
- Shorten section
- Regenerate
- View evidence map

---

## 22. Error Handling

Every node must return structured errors.

### Error categories

- Input error
- Schema error
- Retrieval error
- LLM error
- Rendering error
- Compilation error
- PDF parsing error
- Vision error
- Validation failure
- Authorization error
- Storage error

### Retry policy

- Schema-invalid LLM response: one constrained retry
- Network error: limited exponential retry
- Compile error: no blind retry; diagnose first
- Vision failure: deterministic checks still run
- Repeated repair failure: human review
- Maximum graph iteration: hard stop

Never create an infinite agent loop.

---

## 23. Logging and Observability

Log structured events:

```json
{
  "request_id": "",
  "node": "vision_review",
  "status": "completed",
  "duration_ms": 0,
  "model": "",
  "prompt_version": "",
  "iteration": 1,
  "issue_count": 2
}
```

Track:

- Node latency
- Model usage
- Token usage
- Compile duration
- Repair count
- Failure reason
- JD coverage
- Page-fill estimate
- Visual score
- Final approval
- Human edits

Sensitive candidate content must not appear in production logs by default.

---

## 24. Evaluation Framework

Use a fixed evaluation set of at least 20 AI-related JDs:

- AI Engineer
- Agent Engineer
- LLM Engineer
- Applied AI Engineer
- RAG Engineer
- ML Engineer
- AI Research Engineer
- AI Platform Engineer
- Fine-Tuning Engineer
- AI Backend Engineer

### Core metrics

```yaml
compile_success_rate: 100%
exactly_one_page_rate: 100%
unsupported_claim_rate: 0%
ats_text_extraction_rate: 100%
critical_geometry_failure_rate: 0%
average_repair_iterations: "<= 2"
must_have_skill_coverage: report
human_visual_acceptance: report
resume_generation_latency: report
cost_per_resume: report
```

### Portfolio metrics to publish

Only publish measured results:

- Number of benchmark JDs
- One-page success rate
- Compile success rate
- Average self-repair iterations
- Unsupported-claim rate
- Visual defect reduction
- Average generation time
- Average model cost
- Human preference score

---

## 25. Development Milestones

### Milestone 0 — Project contract

Deliver:

- `PLAN.md`
- `memory.md`
- Compact repository
- Tooling
- CI
- Initial failing tests

Exit criteria:

- Test runner works
- Linting works
- Type checking works
- `memory.md` contains the exact next action

### Milestone 1 — Deterministic vertical slice

Build without LLMs:

```text
Fixture JD
→ fixture evidence
→ fixture resume JSON
→ LaTeX
→ PDF
→ page validation
→ screenshot
```

Exit criteria:

- Exactly one-page PDF
- Full test coverage of rendering and validation
- No live API dependency

### Milestone 2 — JD and evidence intelligence

Add:

- Structured JD analyzer
- Evidence store
- Matching
- Strategy
- Space planning

Exit criteria:

- Fixed JDs produce expected evidence rankings
- No unsupported evidence accepted

### Milestone 3 — Structured writing

Add:

- Writer prompt
- Pydantic contracts
- Claim provenance
- Role-tailored content

Exit criteria:

- Every bullet contains valid evidence IDs
- Writer respects line budgets
- Golden test fixtures pass

### Milestone 4 — Agentic repair loop

Add:

- LangGraph graph
- Conditional routing
- Geometry issues
- Targeted repair
- Bounded iteration

Exit criteria:

- Known overflow fixture repairs itself
- Unaffected elements remain unchanged
- Maximum iteration is enforced

### Milestone 5 — Vision QA

Add:

- Screenshot renderer
- Vision critic
- Vision contract
- Combined vision/geometry policy

Exit criteria:

- Curated visual defects are detected
- Vision cannot override hard deterministic constraints
- Live evaluations are recorded

### Milestone 6 — Telegram HITL

Add:

- Admin allowlist
- JD ingestion
- Status messages
- PDF preview
- Approval and edit commands
- Checkpoint resume

Exit criteria:

- Full private mobile workflow works
- Unauthorized user is rejected
- User edits trigger targeted revalidation

### Milestone 7 — Evaluation and portfolio release

Deliver:

- Benchmark suite
- Evaluation report
- Architecture diagram
- Demo video
- README
- Example input/output
- Public-safe sample candidate profile

Exit criteria:

- Published metrics are reproducible
- Repository setup is documented
- No personal secrets are committed

---

## 26. Definition of Done

A feature is done only when:

- Its required behavior is stated in plain language
- A failing test was written first and observed failing for the expected reason
- The smallest implementation passes
- Focused unit tests pass
- Relevant contract, integration, graph, security, and regression tests pass
- Type checking passes
- Linting passes
- Security implications were considered
- Documentation is updated
- `memory.md` is updated
- Coverage does not regress below policy
- Prompt, schema, and template versions are updated when applicable
- No unsupported behavior was introduced
- The next exact action is recorded

The project is done when:

- A JD can be sent through Telegram
- The system creates a truthful, tailored resume
- The PDF is exactly one page
- The final page passes deterministic checks
- The final page receives multimodal review
- Detected defects are repaired through a bounded loop
- The user can approve or request edits
- The final PDF is returned through Telegram
- The evaluation suite proves the system’s claims

---

## 27. `memory.md` Maintenance Protocol

`memory.md` is the project’s persistent operational memory.

It is not:

- A chat transcript
- A place for speculative ideas
- A duplicate of `PLAN.md`
- A dump of every command
- A replacement for Git history

It must answer:

1. What are we building?
2. What has been decided?
3. What currently works?
4. What currently fails?
5. What was tested?
6. What is the exact next action?
7. Why were important decisions made?

### Mandatory workflow

#### Before starting work

1. Read `PLAN.md`.
2. Read `memory.md`.
3. Confirm the current milestone.
4. Confirm the exact next action.
5. Run the relevant tests.
6. Do not begin unrelated work.

#### After every meaningful coding task

Update:

- Current status
- Files changed
- Tests added
- Tests passed/failed
- Decisions made
- Known issues
- Exact next action

#### At the end of every session

`memory.md` must contain:

- A concise session summary
- Current test status
- Current blocker
- Exact command to continue
- Exact file or test to work on next

### Memory rules

- Keep facts concise.
- Preserve important rationale.
- Never silently reverse a decision.
- Superseded decisions must be marked as superseded.
- Keep an append-only decision log.
- Do not store secrets.
- Do not store full candidate personal data.
- Use paths and identifiers instead of copying large content.
- Archive old session logs when the file becomes too large.
- The “Next Exact Action” section must always contain one primary action.
- Update memory only after tests confirm the claimed state.

### Automated memory checks

Create a test or script that fails when `memory.md` lacks:

- Current milestone
- Test status
- Known issues
- Next exact action
- Last updated date

Suggested command:

```bash
make memory-check
```

---

## 28. Required `memory.md` Structure

```markdown
# Project Memory

## Project Identity
## Current Milestone
## Current Objective
## Non-Negotiable Invariants
## Confirmed Decisions
## Current Architecture
## Implementation Status
## Test Status
## Known Issues
## Current Blocker
## Next Exact Action
## Files Changed Recently
## Prompt Versions
## Metrics Snapshot
## Decision Log
## Session Log
```

---

## 29. Daily Coding Discipline

Start each work session with:

```bash
git status
pytest -q
make memory-check
```

For each feature:

```text
Write failing test
→ run only that test
→ implement minimum code
→ run that test
→ run related suite
→ refactor
→ run full suite
→ update memory.md
→ commit
```

Suggested commit style:

```text
test: define one-page PDF invariant
feat: add deterministic page-count validator
refactor: isolate PDF geometry policy
docs: update project memory after validator milestone
```

---

## 30. First Implementation Sprint

### Goal

Create a deterministic, fully tested vertical slice that produces and validates one compact one-page PDF without using any LLM.

### Tasks

1. Initialize project and tooling.
2. Add settings model and admin-ID test.
3. Add Pydantic models for evidence and resume content.
4. Add evidence-grounding tests.
5. Add a minimal locked LaTeX template.
6. Add safe Jinja2 renderer.
7. Add LaTeX escaping tests.
8. Add compiler wrapper.
9. Add one-page validator.
10. Render a screenshot.
11. Add geometry report.
12. Add `memory-check`.
13. Update `memory.md`.
14. Commit the vertical slice.

### First exact test

```python
def test_resume_policy_requires_exactly_one_page():
    policy = ResumePolicy(page_count=1)
    assert policy.page_count == 1
```

Then add the invalid case:

```python
@pytest.mark.parametrize("page_count", [0, 2, 3])
def test_resume_policy_rejects_any_page_count_other_than_one(page_count):
    with pytest.raises(ValidationError):
        ResumePolicy(page_count=page_count)
```

### Sprint exit command

```bash
pytest -m "not live_llm and not live_vision" -q
ruff check .
ruff format --check .
mypy app
coverage report --fail-under=90
make memory-check
```

All commands must pass before moving to LLM integration.

---


## 31. Detailed TDD Engineering Standard

This section is the mandatory day-to-day development contract for TITAN. The
project is not considered “test-driven” merely because tests exist. Every
production behavior must originate from a test that was first observed failing
for the expected reason.

### 31.1 The only accepted coding loop

```text
1. Specify one observable behavior
2. Write the smallest failing test
3. Run the test and inspect the failure
4. Implement the minimum passing behavior
5. Run the focused test
6. Add boundary and failure cases
7. Refactor with the suite green
8. Run all affected test layers
9. Update memory.md with verified facts
10. Commit one coherent change
```

Do not combine several unrelated features into one red–green cycle.

### 31.2 Behavior-first requirement

Before writing a test, state the behavior in one sentence:

> Given a compiled resume with two pages, when deterministic validation runs,
> TITAN must fail the artifact and route the graph to targeted compression.

That sentence determines:

- What input is required
- Which component owns the behavior
- What observable result proves success
- The lowest sufficient test level
- Which dependency must be replaced with a fake

### 31.3 Test-first proof

A valid TDD change must demonstrate:

- The new test failed before production code changed
- It failed because the behavior was absent, not because the test was broken
- The smallest implementation made it pass
- Nearby negative and boundary cases were added
- Refactoring did not alter behavior
- The full required quality gate passed

A test that was already green does not prove the change.

### 31.4 Feature decomposition

Large tasks must be split into testable behavioral increments.

Bad task:

```text
Implement vision resume repair
```

Correct decomposition:

```text
Reject an unknown visual issue type
Map a valid issue to an existing element_id
Reject an issue referencing a missing element
Preserve protected terms during repair
Modify only the flagged element
Increment content_version after repair
Stop after max_iterations
Route unresolved defects to manual review
```

### 31.5 Test taxonomy

#### Unit tests

Pure logic with no network, model, Telegram, database, or real compiler.

Examples:

- JD normalization
- Skill aliases
- Evidence scoring
- Space-budget calculations
- Route precedence
- LaTeX escaping
- Margin arithmetic
- Issue deduplication
- State immutability

#### Contract tests

Validate every external or model-facing boundary:

- LLM input/output schema
- Vision output schema
- Telegram gateway payload
- Compiler result structure
- Storage interface
- Prompt version metadata

Default CI uses stored fixtures, never paid model calls.

#### Integration tests

Test real component boundaries:

- Resume JSON → Jinja2 → `.tex`
- `.tex` → real compiler → PDF
- PDF → text and geometry report
- SQLite candidate store → evidence matcher
- Checkpoint → restored LangGraph state

#### Graph tests

Test each node independently, then test conditional edges and complete bounded
cycles.

#### Regression tests

Protect accepted behavior using representative JDs, profiles, resume content,
PDF geometry reports, visual issue fixtures, and graph traces.

#### Security tests

Cover authorization, prompt injection, LaTeX injection, compiler sandboxing,
file limits, redacted logs, and replayed Telegram updates.

#### Live evaluation tests

Real text or vision model calls are opt-in and versioned. They evaluate model
quality; they do not replace deterministic contracts.

### 31.6 Test pyramid

```text
                    Few live E2E evaluations
                 Few deterministic E2E tests
                Graph and integration tests
              Contract and regression fixtures
           Many unit and property-based tests
```

Target distribution:

```yaml
unit_and_property_tests: 60-70%
contract_tests: 15-20%
integration_and_graph_tests: 10-15%
end_to_end_and_live_tests: 5% or less
```

### 31.7 Test naming

Use:

```text
test_<subject>_<condition>_<expected_behavior>
```

Good:

```python
def test_page_validator_rejects_two_page_pdf():
    ...

def test_writer_rejects_unknown_evidence_id():
    ...

def test_targeted_repair_preserves_unflagged_elements():
    ...

def test_router_prioritizes_unsupported_claim_over_visual_pass():
    ...
```

Bad:

```python
def test_resume():
    ...

def test_success():
    ...
```

### 31.8 Arrange–Act–Assert

```python
def test_page_validator_rejects_two_page_pdf(two_page_pdf):
    # Arrange
    validator = PdfValidator(policy=ResumePolicy())

    # Act
    report = validator.validate(two_page_pdf)

    # Assert
    assert report.passed is False
    assert report.page_count == 2
    assert report.primary_issue.issue_type == "page_overflow"
```

One test should have one primary failure reason.

### 31.9 Required test doubles

Prefer dependency injection and explicit test doubles:

```text
InMemoryCandidateStore
FakeLLMClient
FakeVisionClient
FakeTelegramGateway
RecordedCompiler
FixedClock
DeterministicIdGenerator
```

Definitions:

- **Stub:** returns fixed data
- **Fake:** lightweight working implementation
- **Spy:** records interactions
- **Mock:** enforces an interaction contract

Do not patch deep internal functions when a clean protocol can be injected.

### 31.10 Determinism policy

Default tests must control:

- Time
- UUIDs
- Random seeds
- Environment variables
- Model output
- File paths
- Locale
- Template version
- Prompt version
- Compiler version
- Font availability

Every evaluation artifact should record:

```json
{
  "template_version": "resume_v1",
  "prompt_version": "writer_v1",
  "fixture_version": "ai_engineer_001",
  "seed": 42
}
```

### 31.11 TDD for every LangGraph node

Each node is first tested as a state transformation.

Required cases:

1. Valid state → expected state delta
2. Missing input → explicit typed failure
3. Invalid dependency output → schema failure
4. Unrelated state remains unchanged
5. Structured event is logged
6. Retry behavior is bounded
7. Idempotency is verified where necessary

Example:

```python
def test_match_evidence_adds_ranked_matches_without_mutating_raw_jd():
    state = make_state(
        raw_jd_text="Build LangGraph agent workflows",
        structured_jd=make_jd(must_have_skills=["LangGraph"]),
    )

    result = match_evidence(state, store=matching_store())

    assert result["evidence_matches"][0]["evidence_id"] == "blackcoat_langgraph_001"
    assert result["raw_jd_text"] == state["raw_jd_text"]
```

### 31.12 TDD for conditional routing

Use table-driven tests:

```python
@pytest.mark.parametrize(
    ("state", "expected_route"),
    [
        (state_with_compile_failure(), "repair_rendering"),
        (state_with_two_pages(), "targeted_repair"),
        (state_with_unsupported_claim(), "targeted_repair"),
        (state_with_all_gates_passed(), "request_approval"),
        (state_at_iteration_limit(), "request_manual_review"),
    ],
)
def test_decide_next_action_routes_by_failure_priority(state, expected_route):
    assert decide_next_action(state) == expected_route
```

Route precedence must be explicit. A high visual score can never override an
unsupported claim or a two-page failure.

### 31.13 TDD for LLM-backed nodes

Treat the model as an unreliable external service.

Each LLM-backed node requires tests for:

- Correct request payload
- Strict response parsing
- Unknown evidence IDs
- Missing required fields
- One constrained retry for malformed schema
- No retry for policy violation
- Timeout
- Provider error
- Redacted logging
- Prompt version recording

```python
async def test_writer_retries_once_after_invalid_schema():
    client = FakeLLMClient(
        responses=[{"invalid": "payload"}, valid_resume_response()]
    )

    result = await writer.generate(writer_request())

    assert result == expected_resume_content()
    assert client.call_count == 2
```

### 31.14 Prompts are versioned production code

A prompt change requires:

1. A failing or degraded regression case
2. A minimal prompt modification
3. Contract-test execution
4. Curated evaluation execution
5. Comparison against the previous prompt version
6. Changelog entry
7. `memory.md` update

Each prompt file must declare:

```yaml
name: writer
version: 1.0.0
purpose: Generate evidence-grounded resume content
input_schema: WriterRequest
output_schema: ResumeContent
```

Never silently change prompt behavior.

### 31.15 TDD for LaTeX and PDF generation

Test source safety and rendered properties.

Required cases:

- Reserved-character escaping
- Unicode normalization
- Missing field failure
- Unsafe LaTeX command rejection
- Shell escape disabled
- Compiler timeout
- Invalid `.tex` structured error
- Exactly one page
- Extractable ATS text
- Correct section order
- Minimum font size
- Safe page boundaries
- Valid links
- Stable element identifiers

Use the real compiler in integration tests. Use a fake only for unit-level
routing and failure-policy tests.

### 31.16 Golden PDF policy

Do not assert byte-identical PDF output across platforms.

Compare:

```text
page count
extracted text
section sequence
font-size range
bounding-box tolerances
left and right alignment
minimum margins
issue classifications
```

A golden update requires a documented explanation. Do not approve a new golden
artifact simply because the old test failed.

### 31.17 TDD for vision review

Split vision testing into two layers.

#### Offline contract layer

Stored responses test:

- Valid issue parsing
- Invalid severity
- Unknown element ID
- Conflicting recommendations
- Duplicate issue handling
- Timeout and provider failure
- Repair routing

#### Live evaluation layer

```bash
pytest -m live_vision
```

Use a labelled defect set:

- Dense bullet
- Misaligned dates
- Uneven whitespace
- Weak hierarchy
- Tiny body text
- Unsafe margins
- Clipping
- Overlap

Track defect-detection precision and recall. Live vision tests are not part of
the fast default suite.

### 31.18 TDD for targeted repair

The repair engine must prove:

- Only flagged elements change
- Evidence IDs are preserved
- Protected terms are preserved
- No metric is invented
- Content version increments
- Before/after text is recorded
- Repair count increments
- Maximum iterations stop the loop

```python
def test_targeted_repair_changes_only_flagged_element():
    before = resume_with_three_bullets()

    after = repair(
        before,
        issue=overflow_issue("projects.dex_jobs.bullet_2"),
    )

    assert changed_element_ids(before, after) == {
        "projects.dex_jobs.bullet_2"
    }
```

### 31.19 Property-based tests

Use Hypothesis for large input spaces:

- LaTeX escaping
- Unicode normalization
- Evidence-ID collections
- JD whitespace normalization
- Margin calculations
- Line budgets
- Repair immutability

```python
@given(st.text())
def test_latex_escape_never_emits_unsafe_unescaped_text(text):
    assert is_safe_latex_text(escape_latex(text))
```

### 31.20 Mutation testing

After the deterministic core is stable, mutation testing must verify that tests
protect critical rules.

The suite must fail if a mutation:

- Changes `page_count == 1` to `page_count >= 1`
- Removes evidence validation
- Disables authorization
- Reverses graph route precedence
- Removes safe-margin failure
- Allows unrelated elements to change during repair

Run mutation testing periodically or before releases.

### 31.21 Coverage policy

Coverage is a diagnostic, not a substitute for meaningful tests.

```yaml
overall_line_coverage: 90%
overall_branch_coverage: 85%
critical_domain_line_coverage: 100%
critical_domain_branch_coverage: 95%
```

Critical modules:

- Resume policy
- Evidence provenance
- Graph routing
- Targeted repair
- LaTeX escaping
- Compiler sandbox
- PDF validation
- Telegram authorization

### 31.22 Test markers and commands

Markers:

```text
unit
contract
integration
compiler
graph
regression
security
visual
slow
live_llm
live_vision
```

Default local suite:

```bash
pytest -m "not live_llm and not live_vision" -q
```

Focused TDD cycle:

```bash
pytest tests/unit/test_resume_policy.py -q
```

Compiler integration:

```bash
pytest -m compiler -q
```

Live evaluation:

```bash
pytest -m "live_llm or live_vision" -q
```

### 31.23 CI merge gates

Every pull request must pass:

```bash
pytest tests/unit tests/contract -q
pytest tests/integration -q
ruff check .
ruff format --check .
mypy app
coverage report --fail-under=90
make memory-check
```

The compiler job must use a pinned container with fixed:

- LaTeX engine
- System packages
- Fonts
- Locale
- Python version

Scheduled or manual jobs run:

```bash
pytest -m regression
pytest -m security
pytest -m live_llm
pytest -m live_vision
```

A merge is blocked when:

- Required tests fail
- Coverage drops below policy
- Type checking fails
- Formatting or linting fails
- `memory.md` is stale
- Prompt changed without version update
- Schema changed without contract tests
- Template changed without PDF regression tests

### 31.24 Bug-fix protocol

Every defect follows:

```text
Reproduce with a failing test
→ classify the root cause
→ implement the smallest fix
→ add a boundary test
→ run regression tests
→ update memory.md
```

Do not patch a prompt when the actual defect belongs in routing, validation,
schema enforcement, escaping, or geometry policy.

### 31.25 Refactoring protocol

Refactor only from a green suite.

Before refactoring:

- Add characterization tests if behavior is unclear
- Identify the exact duplication or design problem
- Keep behavioral and architectural changes separate

After refactoring:

- Run focused tests
- Run affected integration tests
- Run type, lint, and coverage gates
- Confirm golden outputs did not change unexpectedly

### 31.26 Pull-request evidence

Every PR must contain:

```markdown
## Behavior added or fixed
## Failing test written first
## Focused test command
## Full verification command
## Fixtures changed
## Prompt/schema/template version changes
## memory.md update
```

### 31.27 Feature-to-test matrix

| Feature | First failing test | Required follow-up tests |
|---|---|---|
| JD ingestion | Blank JD is rejected | size limit, normalization, duplicates |
| JD analysis | Missing role fails schema | retry, malformed output, injection |
| Evidence store | Disabled evidence is excluded | aliases, confidence, metrics |
| Evidence matching | Exact LangGraph match ranks first | partial match, tie, missing match |
| Space planner | Bullet count is bounded | overflow, underfill, minimum sections |
| Writer | Bullet needs valid evidence ID | protected terms, no invented metric |
| Renderer | Reserved LaTeX chars are escaped | Unicode, missing fields, versioning |
| Compiler | Invalid TeX returns structured error | timeout, shell escape, logs |
| Page validator | Two-page PDF fails | zero pages, parsing failure |
| Geometry | Unsafe margin is detected | alignment, clipping, overlap |
| Vision critic | Unknown element ID is rejected | conflict, timeout, duplicates |
| Repair | Only flagged element changes | evidence preservation, max attempts |
| Router | Overflow routes to repair | precedence, manual-review stop |
| Telegram | Unauthorized user is rejected | replay, approval, edit |
| Memory check | Missing next action fails | stale date, missing test status |

### 31.28 Milestone TDD exit gates

No milestone closes merely because code exists.

#### Milestone 0

- CI can demonstrate a failing test
- Test markers are configured
- Coverage reporting works
- `memory-check` works

#### Milestone 1

- Deterministic E2E fixture produces exactly one page
- Invalid TeX, timeout, two-page, and unsafe-margin cases are tested
- No live model dependency

#### Milestone 2

- Evidence rankings are protected by golden tests
- Unsupported evidence is impossible
- Alias and tie-break behavior is tested

#### Milestone 3

- Every generated bullet has provenance
- Prompt contracts and retry paths are tested
- Writer regression fixtures pass

#### Milestone 4

- Route precedence is fully table-tested
- Repair changes only flagged elements
- Checkpoint recovery works
- Iteration limits are enforced

#### Milestone 5

- Vision contracts pass offline
- Live defect evaluations are versioned
- Geometry retains veto authority

#### Milestone 6

- Unauthorized and replayed Telegram requests fail
- Approval cannot bypass quality gates
- Deterministic E2E uses a fake Telegram gateway

#### Milestone 7

- Published metrics reproduce from one documented command
- Regression, security, mutation, and evaluation gates pass

### 31.29 Trustworthy-test checklist

A test is trustworthy only when it:

- Fails when the protected behavior is removed
- Passes for the intended reason
- Uses deterministic input
- Is independent of test order
- Produces a useful failure
- Tests behavior, not private implementation details
- Uses the lowest sufficient test layer
- Is affordable for its CI stage

---

## 32. Final Engineering Principle

The project should remain simple at the infrastructure level and sophisticated at the reasoning-and-evaluation level.

Do not increase complexity to look advanced.

The strongest architecture is:

```text
Small codebase
+ strict schemas
+ verified evidence
+ deterministic compiler
+ measurable geometry
+ one focused vision critic
+ bounded LangGraph repair loop
+ strong tests
```

The final product must prove:

> TITAN can select the right evidence, write the right content, fit it into exactly one page, inspect the actual rendered result, and reliably repair defects without fabricating information.
