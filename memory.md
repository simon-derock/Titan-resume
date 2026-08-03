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
safe LaTeX text escaping is implemented, while template rendering and artifact
validation are not yet implemented.

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
- `scripts.check_memory` validates required operational memory.
- CI and Make targets define the initial quality gates.

## Test Status

The complete local test, lint, type, and memory gates pass: 22 tests with 99.24%
branch-aware coverage.

## Known Issues

- No LaTeX engine is installed, so real compiler integration is not yet possible.
- The deterministic rendering, compilation, PDF validation, screenshot, and
  geometry slice is not implemented.

## Current Blocker

No blocker for Milestone 0. A LaTeX engine is required before Milestone 1 can
satisfy its real-compiler exit criterion.

## Next Exact Action

Write and observe the failing integration test that renders structured resume
content through the locked `resume_v1` Jinja2 template without exposing raw
candidate LaTeX.

## Files Changed Recently

- `pyproject.toml`, `Makefile`, `.github/workflows/ci.yml`
- `app/models.py`, `app/config.py`
- `scripts/check_memory.py`
- `tests/unit/test_resume_policy.py`, `tests/unit/test_config.py`
- `tests/unit/test_memory_check.py`

## Prompt Versions

No prompts exist yet.

## Metrics Snapshot

- Tests passing: 22
- Measured line and branch coverage: 99.24%
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

## Session Log

- 2026-08-03: Read the full plan, inspected the empty repository, recorded the
  missing toolchain, completed the first policy/configuration/memory red–green
  cycles, and established the initial CI contract.
- 2026-08-03: Pushed the Milestone 0 red/green history to `origin/main`; added and
  verified the first Milestone 1 evidence-grounding increment.
