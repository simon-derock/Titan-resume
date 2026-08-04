# Project Memory

Last updated: 2026-08-04

## Project Identity

TITAN is an evidence-grounded, self-correcting compiler for truthful,
ATS-readable, exactly one-page resumes. The primary interface will be a private
Telegram bot; the deterministic document pipeline comes first.

## Current Milestone

Milestone 3 — Structured writing.

## Current Objective

Version the first writer prompt and provider adapter contract on top of the fully
validated structured writer boundary, while retaining fake-client coverage and
keeping live calls disabled by default.

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

Milestones 0 and 1 are complete. The deterministic domain layer now has
immutable policy, evidence, bullet, entry, and versioned resume-content models;
safe LaTeX escaping, locked-template rendering, restricted PDF compilation, and
typed page-count validation are implemented. Real `pdfinfo` metadata is wired;
high-resolution first-page PNG rendering is wired; ATS text extraction and
PDF-coordinate extraction are wired. The next step is composing these verified
components into one deterministic vertical-slice workflow. That composition is
implemented, and CI now provisions the pinned, hash-verified Tectonic compiler
and warms the locked-template support cache before executing real compiler tests.

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
- `scripts.check_memory` validates required operational memory.
- CI and Make targets define the initial quality gates.

## Test Status

The complete local gate passes 129 tests with 100% line and branch coverage,
including real compilation, page metadata, PNG, coordinate extraction, and
safe-margin, ATS, end-to-end vertical-slice, CI provisioning, and private
candidate-store validation, plus deterministic JD intake, schema, and evidence
matching, bounded space-planning, grounded strategy, and offline structured-JD
analysis contracts. A golden integration proves stable rankings and preserves
Kubernetes as an unsupported must-have gap; writer tests prove it cannot re-enter
content through a provider response.

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

## Current Blocker

No engineering blocker. A live model provider and real target JD are not selected;
prompt and adapter contracts remain provider-neutral and offline-testable.

## Next Exact Action

Add a failing `tests/contract/test_writer_prompt.py` contract for a versioned
writer prompt that explicitly requires structured JSON, selected evidence IDs,
line budgets, protected terms, `must_not_claim`, and no LaTeX.

## Files Changed Recently

- `app/models.py`, `app/services/writing.py`
- `tests/unit/test_structured_writer.py`
- `memory.md`

## Prompt Versions

No prompts exist yet.

## Metrics Snapshot

- Tests passing: 129
- Tests failing: 0
- Measured line and branch coverage: 100.00%
- Live model calls: 0
- Compiled resume fixtures: 1
- Golden JD intelligence fixtures: 1

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
