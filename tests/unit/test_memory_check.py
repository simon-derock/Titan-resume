from pathlib import Path

import pytest

from scripts.check_memory import MemoryContractError, main, validate_memory

VALID_MEMORY = """\
# Project Memory

Last updated: 2026-08-03

## Current Milestone
Milestone 0

## Test Status
Passing.

## Known Issues
None.

## Next Exact Action
Run the focused test.
"""


@pytest.mark.unit
def test_memory_check_accepts_required_operational_sections() -> None:
    validate_memory(VALID_MEMORY)


@pytest.mark.unit
def test_memory_check_rejects_missing_next_exact_action() -> None:
    memory_without_next_action = VALID_MEMORY.replace(
        "## Next Exact Action\nRun the focused test.\n", ""
    )

    with pytest.raises(MemoryContractError, match="Next Exact Action"):
        validate_memory(memory_without_next_action)


@pytest.mark.unit
def test_memory_check_rejects_missing_last_updated_date() -> None:
    memory_without_date = VALID_MEMORY.replace("Last updated: 2026-08-03\n", "")

    with pytest.raises(MemoryContractError, match="Last updated date"):
        validate_memory(memory_without_date)


@pytest.mark.unit
def test_memory_check_cli_accepts_valid_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    memory_path = tmp_path / "memory.md"
    memory_path.write_text(VALID_MEMORY, encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["check_memory", str(memory_path)])

    assert main() == 0


@pytest.mark.unit
def test_memory_check_cli_exits_for_missing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing_path = tmp_path / "missing.md"
    monkeypatch.setattr("sys.argv", ["check_memory", str(missing_path)])

    with pytest.raises(SystemExit) as error:
        main()

    assert error.value.code == 1
