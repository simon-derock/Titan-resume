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
safe LaTeX escaping and locked-template rendering are implemented, while PDF
compilation has a restricted subprocess wrapper; real PDF artifact validation is
not yet implemented.

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
- `scripts.check_memory` validates required operational memory.
- CI and Make targets define the initial quality gates.

## Test Status

The previous complete gate passed 29 tests with 99.49% branch-aware coverage.
The new Tectonic command-policy unit test passes; the real compiler test is RED
because its required support bundle has not yet been cached.

## Known Issues

- System TeX installation was unavailable without an interactive sudo password;
  a hash-verified workspace-local Tectonic engine is installed instead.
- Tectonic's support bundle is not cached yet, so the real compiler integration
  test fails safely in cache-only mode.
- PDF validation, screenshot rendering, and geometry reporting are not
  implemented.

## Current Blocker

Real compiler integration is blocked until Tectonic's support bundle is fetched
once into the ignored workspace cache. Restricted compilation correctly refuses
network access at runtime.

## Next Exact Action

Warm `.tools/tectonic-cache` from the official Tectonic bundle, then rerun
`tests/integration/test_real_compiler.py` and diagnose any template failure.

## Files Changed Recently

- `pyproject.toml`, `Makefile`, `.github/workflows/ci.yml`
- `app/models.py`, `app/config.py`
- `app/services/rendering.py`, `templates/resume_v1.tex.j2`
- `scripts/check_memory.py`
- `tests/unit/test_compiler.py`, `tests/integration/test_real_compiler.py`

## Prompt Versions

No prompts exist yet.

## Metrics Snapshot

- Tests passing: 30
- Tests failing: 1 real compiler integration (support cache absent)
- Measured line and branch coverage: 99.49%
- Live model calls: 0
- Compiled resume fixtures: 0

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

## Session Log

- 2026-08-03: Read the full plan, inspected the empty repository, recorded the
  missing toolchain, completed the first policy/configuration/memory red–green
  cycles, and established the initial CI contract.
- 2026-08-03: Pushed the Milestone 0 red/green history to `origin/main`; added and
  verified the first Milestone 1 evidence-grounding increment.
