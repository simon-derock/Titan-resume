# Project Memory

Last updated: 2026-08-11

## Project Identity

TITAN is an evidence-grounded, self-correcting compiler for truthful,
ATS-readable, exactly one-page resumes. The primary interface will be a private
Telegram bot; the deterministic document pipeline comes first.

## Current Milestone

Resume-quality evaluation loop — benchmark and deterministic quality gates.

## Current Objective

Raise generated resume quality above the user-designated handmade resume before
continuing Telegram work. The loop prioritizes evidence richness, JD targeting,
page utilization, typography, working links, ATS extraction, and deterministic
repair of sparse or visually weak output.

## Non-Negotiable Invariants

- Resume output is exactly one page.
- Every generated claim traces to allowed evidence.
- Raw model-generated LaTeX is forbidden.
- Deterministic validators can veto model advice.
- Repair loops are bounded.
- Production behavior begins with an observed failing test.

## Confirmed Decisions

- The canonical Git remote is
  `https://github.com/simon-derock/Titan-resume.git` on the `main` branch.
- `TITAN_PLAN.md` and `memory.md` are intentionally tracked and may be pushed.
- Commit history must make TDD visible with focused test-first and implementation
  commits; messages must be concise, professional, and human-written in tone.
- The distribution is `titan-resume`; the initial Python application package is
  `app`, matching the compact layout in `TITAN_PLAN.md`.
- Python 3.11 is the minimum supported version.
- Pydantic v2 owns strict domain and configuration validation.
- Default tests exclude live language and vision model calls.

## Current Architecture

Milestones 0–3 are complete. The deterministic domain layer has immutable
policy, evidence, bullet, entry, and versioned resume-content models; safe LaTeX
escaping, three-template Jinja2 rendering, restricted PDF compilation, and typed
page-count validation. Real `pdfinfo`, ATS extraction, geometry, and first-page
PNG rendering are wired. CI provisions and warms Tectonic 0.16.9. The three
supported templates are `resume_v1` (single-column A4), `moderncv_two_column_v1`
(banking-style two-column A4, implemented with stable article primitives due to
a Tectonic 0.16.9 `free(): invalid pointer` crash in moderncv's FontAwesome
dependency), and `deedy_cv_v1` (two-column A4, Apache-2.0, `\scshape` replaced
with `\MakeUppercase` and `$\vert$` replaced with `\textbar{}` for text-mode
safety). Reference source files are tracked under `latex_templates/` for design
provenance and attribution; they are not used at compilation time.

## Implementation Status

- Project metadata and a local uv environment are present.
- `ResumePolicy` enforces `page_count == 1`.
- `Settings` rejects an empty Telegram admin allowlist.
- Resume bullets require evidence IDs, and cross-record validation rejects IDs
  that are missing or not allowed for resume use.
- `ResumeContent` is strict, template-locked, versioned, renderer-independent,
  and recursively checked for unavailable evidence references.
- Candidate-controlled LaTeX reserved characters and command prefixes are
  escaped deterministically before template rendering.
- `LatexRenderer` uses a sandboxed, strict Jinja2 environment and the versioned
  `resume_v1` template with deterministic element markers.
- `LatexCompiler` uses fixed list arguments, explicitly disables shell escape,
  enforces a timeout, and returns typed success, compile, timeout, or unavailable
  engine results through an injectable process runner.
- The compiler supports explicit pdfLaTeX and Tectonic policies. Tectonic runs
  with `--untrusted` and `--only-cached`; the verified local engine is upstream
  Tectonic 0.16.9 (Linux x86-64 archive SHA-256
  `f3c825128095dc3399ea11c08c18035b33050a216930c295c79e8eb11bd21de4`).
- `PdfValidator` accepts exactly one parsed page, rejects overflow with a fatal
  `page_overflow`, and reports malformed metadata as a fatal parse issue.
- The default PDF metadata reader invokes `pdfinfo` with fixed list arguments and
  no shell; a compiled two-page fixture is rejected through the real boundary.
- `PdfScreenshotRenderer` invokes `pdftoppm` with fixed page and DPI arguments,
  reports raster failures explicitly, and preserves the A4 page ratio at 200 DPI.
- `GeometryValidator` measures all four page edges from element text boxes and
  emits fatal `unsafe_margin` issues below the configured safety thresholds.
- `GeometryValidator` rejects more than 60 pt of unused bottom space with a
  high-severity `excessive_bottom_whitespace` issue. Sparse compiler-only test
  fixtures explicitly opt out; the production pipeline uses the quality gate.
- `PdfGeometryExtractor` parses first-page `pdftotext -bbox` XHTML into typed
  page dimensions and deterministic word-level boxes, rejecting tool, schema,
  empty-page, and malformed-coordinate failures explicitly.
- `PdfTextExtractor` uses first-page layout mode, while `AtsTextValidator`
  rejects blank text, missing sections, and non-logical section order.
- `DeterministicResumePipeline` validates provenance, renders, compiles, applies
  page/ATS/geometry gates, renders the preview, and returns one typed artifact
  result. Compile and page failures stop downstream work.
- CI installs Tectonic 0.16.9 from the verified upstream archive, checks its
  SHA-256 digest, and warms the exact package/font surface used by the locked
  template before tests execute cache-only compilation.
- `Philip_Simon_Derock_AI_Engineer_Resume.pdf` is the user-designated current
  source resume. It remains local and ignored because it contains personal data.
  It is one US Letter page with extractable text; its two-column layout produces
  an interleaved ATS reading order and is not the locked A4 output template.
- `JsonCandidateEvidenceStore` validates local JSON through the strict evidence
  model, returns only resume-allowed records in stable identifier order, rejects
  duplicate IDs, and sanitizes unavailable or malformed private-store errors.
- `JobDescriptionIngester` enforces configurable input bounds, normalizes line
  endings and whitespace, removes exact duplicate blocks, and hashes normalized
  content with SHA-256. `StructuredJobDescription` provides a strict, immutable
  contract for grouped requirements without performing any model call.
- `EvidenceMatcher` considers only structured skills on resume-allowed evidence,
  resolves a fixed explicit alias set, aggregates compound requirements, reports
  strong/partial/missing coverage, and uses evidence IDs as stable tie-breakers.
  Claim prose is never keyword-mined as proof of a skill.
- `SpacePlanner` reserves a reviewed 47-line page budget and caps the initial
  template at three experience entries with three bullets each, three projects
  with two bullets each, and one education entry. Runtime inventory cannot raise
  those limits, and section reservations cannot exceed the page limit.
- `ResumeStrategyBuilder` rejects unknown or disallowed match references, ranks
  must-have evidence above preferred evidence, applies source and bullet limits,
  maps supported evidence into template sections, and carries partial or missing
  must-haves forward as explicit `must_not_claim` constraints.
- `StructuredJobDescriptionAnalyzer` accepts a provider-neutral typed client,
  injects or verifies the canonical ingested-JD hash, validates every response
  through `StructuredJobDescription`, retries provider/schema failures at most
  three times, and emits a sanitized typed failure after exhaustion.
- `JobEvidenceIntelligencePipeline` composes normalized JD ingestion, fake or
  replaceable structured analysis, resume-allowed evidence loading, conservative
  matching, unique-source inventory, bounded space planning, and grounded
  strategy into one serializable Milestone 2 result.
- `StructuredResumeWriter` exposes only strategy-selected evidence and a strategy
  with omitted IDs removed, validates responses through `ResumeContent`, rejects
  unavailable provenance, unsupported `must_not_claim` terms, raw LaTeX, foreign
  roles, section/entry/bullet/line overflow, and retries at most three times with
  sanitized terminal errors.
- Three production Jinja2 templates are implemented: `resume_v1.tex.j2`,
  `moderncv_two_column_v1.tex.j2`, and `deedy_cv_v1.tex.j2`. Each compiles
  under Tectonic 0.16.9 `--untrusted --only-cached` and passes one-page, ATS
  text extraction, and geometry validation.
- The `compiler_warmup.tex` fixture now covers `tabularx`, `mathpazo`, and
  `helvet` package surface required by the two-column templates.
- `app/prompts/writer_v1.py` exposes `PROMPT_VERSION = 'writer_v1.0'` and a
  pure deterministic `render(request)` function that injects: JSON-only
  output constraint, no-LaTeX prohibition, selected evidence IDs and claims,
  space budget ceilings (line/entry/bullet per section), `must_not_claim`
  terms framed as prohibitions, target role, template_id, schema_version,
  and the expected JSON response schema. No randomness or external I/O.
- `app/services/providers.py` defines `CompletionsBackend` (Protocol),
  `FakeResumeWriterAdapterClient` (test double), and `PromptResumeWriterClient`
  (real adapter delegating prompt construction to `writer_v1.render()`;
  credentials live in the injected backend, never on the adapter class).
- `app/graph.py` defines `ResumeGraphState` (TypedDict with required keys:
  request_id, raw_jd_text, status, iteration, max_repair_cycles,
  pipeline_result, issues, resume_content, repair_feedback) and
  `ResumeGraphExecutor` (injectable writer + pipeline, max_repair_cycles
  1-3, bounded repair loop). Routing: pass -> 'passed', compile_failure ->
  stops immediately (no retry), validation_failure -> repair within budget,
  exhausted budget -> 'needs_review', writer error -> 'write_failed'.
  Pure Python; no LangGraph dependency required until HITL checkpointing.
- CI and Make targets define the initial quality gates.
- `tests/fixtures/jds/ai_engineer_benchmark_v1.json` contains five paraphrased,
  provenance-backed AI Engineer postings from LinkedIn, Indeed, Wellfound, and
  Google Careers spanning entry, mid, and senior expectations.

## Test Status

The complete non-live suite passes 189 tests with three live tests deselected.
Live model and vision call counts remain zero. The files changed by the current
quality increment pass focused Ruff checks and formatting. Repository-wide Ruff
still reports pre-existing issues in committed Gemini/Telegram files and a
user-owned uncommitted writer change.

## Known Issues

- System TeX installation was unavailable without an interactive sudo password;
  a hash-verified workspace-local Tectonic engine is installed instead.
- Minimum font-size and detailed alignment checks are not implemented.
- No CLI exists yet; the typed pipeline is directly callable.
- Claims extracted from the supplied resume are candidate-provided source
  material and must not become resume-allowed evidence without explicit review.
- The supplied resume fails the locked quality policy despite being one page:
  section reading order is invalid, while measured left/right/top margins are
  17.4/2.501/14.195 pt against 22/22/18 pt minimums.
- The current generated resume uses only about 63% of the A4 page and is now
  correctly rejected by the default geometry policy.
- Space planning still caps output at three experience entries and three
  projects regardless of template or measured underfill.

## Current Blocker

No resume-quality engineering blocker. Telegram work is intentionally deferred
by user direction until generated resume quality reaches the reference bar.

## Next Exact Action

Add failing template-aware space-planning tests proving an underfilled
two-column resume can retain all five verified experience entries and restore
additional high-value projects without weakening the exactly-one-page gate.

## Files Changed Recently

- `app/models.py`
- `app/services/validation.py`
- `tests/fixtures/jds/ai_engineer_benchmark_v1.json`
- `tests/regression/test_ai_engineer_benchmark.py`
- `tests/unit/test_geometry.py`
- `memory.md`

## Prompt Versions

- `writer_v1.0`

## Metrics Snapshot

- Tests passing: 189
- Tests failing: 0
- Live model calls: 0
- Live vision calls: 0
- Compiled resume fixtures: 3 (one per supported template)
- Golden JD intelligence fixtures: 1
- Sourced AI Engineer benchmark JDs: 5
- Supported templates: 3 (resume_v1, moderncv_two_column_v1, deedy_cv_v1)
- Prompt versions: 1 (writer_v1.0)
- Graph executor max_repair_cycles: 2 (configurable, cap 3)

## Decision Log

- 2026-08-03: Started with the one-page invariant because it is the hard product
  constraint and the plan's explicit first sprint test.
- 2026-08-03: Used project-local uv tooling so CI and local gates share declared
  versions.
- 2026-08-03: Set the canonical GitHub remote and adopted an auditable red/green
  commit sequence with professional commit messages.
- 2026-08-03: Completed Milestone 0 and began the deterministic slice with
  immutable evidence records and allowlisted cross-reference validation.
- 2026-08-03: Locked resume content to the `resume_v1` structured schema so raw
  LaTeX and unversioned or ungrounded nested content cannot enter rendering.
- 2026-08-03: Implemented character-wise LaTeX escaping so injected commands are
  rendered as literal text rather than executable template source.
- 2026-08-03: Added the versioned single-column A4 template and strict sandboxed
  renderer; template inputs remain structured and element-addressable.
- 2026-08-03: Added restricted LaTeX compilation with explicit shell-escape
  denial, bounded execution, injectable process calls, and typed failure modes.
- 2026-08-03: Chose hash-verified, workspace-local Tectonic after system TeX
  installation required unavailable sudo credentials; runtime compilation stays
  untrusted and cache-only.
- 2026-08-03: Warmed the ignored Tectonic support cache once from the official
  bundle and verified that cache-only compilation produces a real locked-template
  PDF.
- 2026-08-03: Enforced the exactly-one-page invariant as deterministic typed
  validation; no LLM or vision result can override page overflow.
- 2026-08-03: Verified the page-count gate against a real compiled two-page PDF
  using the no-shell `pdfinfo` boundary.
- 2026-08-03: Verified 200-DPI first-page PNG rendering with the A4 aspect ratio
  preserved for Telegram preview and later vision review.
- 2026-08-03: Added geometry-first safe-margin vetoes using explicit PDF-point
  thresholds; perceptual review cannot override these failures.
- 2026-08-04: Integrated real Poppler bounding-box extraction and validated the
  locked compiled page against deterministic safe-margin thresholds.
- 2026-08-04: Verified ATS-readable text and logical section order against a
  fully sectioned compiled fixture.
- 2026-08-04: Composed the deterministic renderer, compiler, page, ATS, geometry,
  and screenshot components into one typed vertical-slice pipeline.
- 2026-08-04: Closed Milestone 1 after CI installed the pinned, hash-verified
  Tectonic toolchain and reproducibly warmed locked-template support files.
- 2026-08-04: Designated the supplied Word-exported resume as a local candidate
  source; preserved it outside version control and recorded its Letter page size
  and two-column ATS-order limitation.
- 2026-08-04: Added a privacy-safe JSON candidate evidence store that exposes
  only explicitly resume-allowed, strictly validated records in deterministic
  order and does not echo malformed private content in error messages.
- 2026-08-04: Measured the supplied resume through the real page, ATS, and
  geometry boundaries; one-page validation passed, while reading order and three
  safe-margin gates correctly failed.
- 2026-08-04: Added bounded, duplicate-aware JD text normalization with stable
  SHA-256 addressing and a strict structured requirement contract; this layer is
  deterministic and introduces no language-model dependency.
- 2026-08-04: Chose conservative structured-skill matching over claim-text
  keyword search so an unsupported skill cannot become evidence merely because
  its name appears in narrative prose; aliases are explicit and versionable.
- 2026-08-04: Locked the initial writer to an explicit 47-line physical budget;
  changing entry or bullet ceilings now requires a reviewed schema change rather
  than an unconstrained runtime value.
- 2026-08-04: Ranked must-have support ahead of confidence and preferences in the
  deterministic strategy layer; incomplete must-haves are propagated as claims
  the writer is forbidden to invent.
- 2026-08-04: Kept the first model-facing boundary provider-neutral and offline;
  the application, not a model, owns JD source hashes, schema validation, retry
  limits, and sanitized terminal failures.
- 2026-08-04: Closed Milestone 2 only after one typed integration proved raw-JD
  normalization, canonical analysis, allowlisted evidence retrieval, stable
  matching, bounded planning, and unsupported-requirement propagation together.
- 2026-08-04: Limited the writer-facing request to selected evidence and removed
  omitted evidence IDs from the provider-visible strategy; provider output is
  untrusted until provenance, claim, role, LaTeX, and space policies all pass.
- 2026-08-05: Expanded the supported template catalog from one to three:
  `resume_v1` (single-column A4), `moderncv_two_column_v1` (banking-style
  two-column), and `deedy_cv_v1` (two-column, Apache-2.0). RED tests first,
  then GREEN implementation.
- 2026-08-05: Chose article-class primitives for the ModernCV production
  adaptation because moderncv.cls triggers a `free(): invalid pointer` crash
  in Tectonic 0.16.9 via its FontAwesome dependency. The reference source is
  retained under `latex_templates/` for attribution.
- 2026-08-05: Replaced `\scshape` with `\MakeUppercase` and `$\vert$` with
  `\textbar{}` across templates to eliminate math-mode leakage in text-mode
  contexts and ensure clean T1-font compilation.
- 2026-08-05: Warmed the Tectonic cache for TS1 Computer Modern 9-point
  metrics (`tcrm0900.tfm`, `cm-super-ts1.enc`, `sfrm0900.pfb`) required by
  the Deedy template's helvet/T1 font surface.
- 2026-08-05: Added `app/prompts/writer_v1.py` with `PROMPT_VERSION` constant
  and deterministic `render()` that injects all safety-critical sections into
  the LLM prompt (JSON-only, no-LaTeX, evidence, budget, must_not_claim).
- 2026-08-06: Added `app/graph.py`: ResumeGraphState TypedDict and
  ResumeGraphExecutor bounded repair state machine. Pure Python, no
  LangGraph dependency. 11 contract tests cover all routing decisions.
  LangGraph wrapping deferred until HITL checkpointing is needed.
- 2026-08-11: Deferred Telegram by explicit user direction and established the
  handmade resume as the minimum richness and visual benchmark for generated
  output.
- 2026-08-11: Set 60 pt as the maximum default bottom whitespace, corresponding
  to approximately 93% A4 page utilization, so a technically one-page but
  materially sparse resume cannot pass deterministic validation.

## Session Log

- 2026-08-03: Read the full plan, inspected the empty repository, recorded the
  missing toolchain, completed the first policy/configuration/memory red–green
  cycles, and established the initial CI contract.
- 2026-08-03: Pushed the Milestone 0 red/green history to `origin/main`; added and
  verified the first Milestone 1 evidence-grounding increment.
- 2026-08-03: Verified the first real LaTeX artifact through Tectonic 0.16.9 with
  untrusted execution and no runtime network access.
- 2026-08-04: Verified real word-level PDF geometry extraction and margin safety.
- 2026-08-04: Verified real ATS text extraction and section-order validation.
- 2026-08-04: Verified the deterministic pipeline's success, compile-failure,
  and page-veto outcomes.
- 2026-08-04: Verified compiler provisioning through a clean RED commit archive,
  then passed 59 tests and all static gates with the GREEN implementation.
- 2026-08-04: Began Milestone 2 with a six-test candidate-store RED/GREEN pair;
  the full repository gate now passes 65 tests at 99.78% coverage.
- 2026-08-04: Completed the JD intake RED/GREEN slice with 81 passing tests and
  99.81% branch-aware coverage; live model and vision call counts remain zero.
- 2026-08-04: Added golden alias, allowlist, compound, claim-isolation, ordering,
  and tie-break tests for evidence matching; 87 tests now pass at 99.83% coverage.
- 2026-08-04: Added the bounded space-planning RED/GREEN pair; 99 tests pass at
  99.84% coverage and live model and vision call counts remain zero.
- 2026-08-04: Added grounded strategy selection and provenance-failure tests;
  104 tests pass at 99.86% coverage with zero live model or vision calls.
- 2026-08-04: Added eight fake-client structured-JD analysis tests; 112 tests pass
  at 99.87% coverage and live model and vision call counts remain zero.
- 2026-08-04: Completed the golden JD evidence-intelligence flow and advanced to
  Milestone 3 with 113 passing tests and zero live model or vision calls.
- 2026-08-04: Completed the grounded structured-writer RED/GREEN slice with 129
  passing tests and 100% line/branch coverage; live model and vision calls remain
  zero.
- 2026-08-05: Resumed the three-template catalog handover: warmed the Tectonic
  cache for TS1 CM metrics; all three templates compiled and passed one-page,
  ATS, and geometry quality gates (142 tests, 100% coverage). Ruff, format,
  mypy, and memory checks all green. Committed and pushed the complete
  RED/GREEN/GREEN template history to origin/main.
- 2026-08-06: Added writer prompt v1 and provider adapter (Milestone 4).
  RED: 28 contract tests committed. GREEN: app/prompts/writer_v1.py and
  app/services/providers.py implemented; all 170 tests pass, Ruff, format,
  mypy, and memory checks green.
- 2026-08-06: Added bounded repair graph executor (Milestone 5).
  RED: 11 contract tests committed. GREEN: app/graph.py implemented with
  ResumeGraphState TypedDict and ResumeGraphExecutor (injectable writer +
  pipeline, compile_failure halts, validation_failure repairs within
  budget, exhausted budget yields needs_review, writer error yields
  write_failed); all 181 tests pass, Ruff, format, mypy, memory clean.
- 2026-08-11: Read the full plan and memory, audited the handmade and generated
  PDFs, researched current AI Engineer postings across four requested job
  platforms, added a five-JD sourced benchmark, and introduced deterministic
  underfill rejection. The non-live suite passes 189 tests.
