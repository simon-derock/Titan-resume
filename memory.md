# Project Memory

Last updated: 2026-08-03

## Project Identity

TITAN is an evidence-grounded, self-correcting compiler for truthful,
ATS-readable, exactly one-page resumes. The primary interface will be a private
Telegram bot; the deterministic document pipeline comes first.

## Current Milestone

Milestone 0 — Project contract and tooling.

## Current Objective

Establish the enforced TDD and operational-memory baseline, then begin the
deterministic vertical slice without live model dependencies.

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

Only the Milestone 0 foundation exists: strict Pydantic policy/settings models,
pytest marker configuration, and a project-memory contract checker.

## Implementation Status

- Project metadata and a local uv environment are present.
- `ResumePolicy` enforces `page_count == 1`.
- `Settings` rejects an empty Telegram admin allowlist.
- `scripts.check_memory` validates required operational memory.
- CI and Make targets define the initial quality gates.

## Test Status

The complete Milestone 0 local gate passes: 10 tests, 100% measured coverage,
Ruff lint and format checks, strict mypy, and `memory-check`.

## Known Issues

- No LaTeX engine is installed, so real compiler integration is not yet possible.
- The deterministic rendering, compilation, PDF validation, screenshot, and
  geometry slice is not implemented.

## Current Blocker

No blocker for Milestone 0. A LaTeX engine is required before Milestone 1 can
satisfy its real-compiler exit criterion.

## Next Exact Action

Write and observe the failing evidence-grounding test for a resume bullet that
references an unknown evidence ID.

## Files Changed Recently

- `pyproject.toml`, `Makefile`, `.github/workflows/ci.yml`
- `app/models.py`, `app/config.py`
- `scripts/check_memory.py`
- `tests/unit/test_resume_policy.py`, `tests/unit/test_config.py`
- `tests/unit/test_memory_check.py`

## Prompt Versions

No prompts exist yet.

## Metrics Snapshot

- Tests passing: 10
- Measured line and branch coverage: 100%
- Live model calls: 0
- Compiled resume fixtures: 0

## Decision Log

- 2026-08-03: Started with the one-page invariant because it is the hard product
  constraint and the plan's explicit first sprint test.
- 2026-08-03: Used project-local uv tooling so CI and local gates share declared
  versions.
- 2026-08-03: Set the canonical GitHub remote and adopted an auditable red/green
  commit sequence with professional commit messages.

## Session Log

- 2026-08-03: Read the full plan, inspected the empty repository, recorded the
  missing toolchain, completed the first policy/configuration/memory red–green
  cycles, and established the initial CI contract.
