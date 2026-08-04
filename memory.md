# Project Memory

Last updated: 2026-08-03

## Project Identity

TITAN is an evidence-grounded, self-correcting compiler for truthful,
ATS-readable, exactly one-page resumes. The primary interface will be a private
Telegram bot; the deterministic document pipeline comes first.

## Current Milestone

Milestone 1 — Deterministic vertical slice.

## Current Objective

Produce and validate a compact one-page PDF from fixture resume JSON without
live model dependencies.

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

The Milestone 0 foundation is complete. The deterministic domain layer now has
immutable policy, evidence, bullet, entry, and versioned resume-content models;
safe LaTeX escaping, locked-template rendering, restricted PDF compilation, and
typed page-count validation are implemented. Real `pdfinfo` metadata is wired;
high-resolution first-page PNG rendering is wired; ATS text extraction and
PDF-coordinate extraction remain. Pure safe-margin geometry policy is
implemented.

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
- `scripts.check_memory` validates required operational memory.
- CI and Make targets define the initial quality gates.

## Test Status

The complete local gate passes 40 tests with 99.68% branch-aware coverage,
including real compilation, page metadata validation, and PNG rendering.

## Known Issues

- System TeX installation was unavailable without an interactive sudo password;
  a hash-verified workspace-local Tectonic engine is installed instead.
- CI does not yet provision the pinned Tectonic binary and support cache, so the
  real compiler test is skipped when that engine is absent.
- PDF text and coordinate extraction are not implemented; geometry policy
  currently consumes validated in-memory boxes.

## Current Blocker

No blocker for PDF coordinate extraction. Reproducible compiler provisioning in CI
remains required before Milestone 1 can close.

## Next Exact Action

Write and observe the failing integration test that extracts real word bounding
boxes and page dimensions from the compiled PDF.

## Files Changed Recently

- `pyproject.toml`, `Makefile`, `.github/workflows/ci.yml`
- `app/models.py`, `app/config.py`
- `app/services/rendering.py`, `templates/resume_v1.tex.j2`
- `scripts/check_memory.py`
- `tests/unit/test_compiler.py`, `tests/integration/test_real_compiler.py`

## Prompt Versions

No prompts exist yet.

## Metrics Snapshot

- Tests passing: 40
- Tests failing: 0
- Measured line and branch coverage: 99.68%
- Live model calls: 0
- Compiled resume fixtures: 1

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

## Session Log

- 2026-08-03: Read the full plan, inspected the empty repository, recorded the
  missing toolchain, completed the first policy/configuration/memory red–green
  cycles, and established the initial CI contract.
- 2026-08-03: Pushed the Milestone 0 red/green history to `origin/main`; added and
  verified the first Milestone 1 evidence-grounding increment.
- 2026-08-03: Verified the first real LaTeX artifact through Tectonic 0.16.9 with
  untrusted execution and no runtime network access.
