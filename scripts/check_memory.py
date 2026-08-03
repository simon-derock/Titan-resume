"""Validate the operational contract recorded in ``memory.md``."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


class MemoryContractError(ValueError):
    """Raised when project memory cannot guide the next work session."""


REQUIRED_SECTIONS = (
    "Current Milestone",
    "Test Status",
    "Known Issues",
    "Next Exact Action",
)
LAST_UPDATED_PATTERN = re.compile(r"(?im)^Last updated:\s*\d{4}-\d{2}-\d{2}\s*$")


def validate_memory(content: str) -> None:
    """Raise a descriptive error when required operational facts are absent."""

    errors: list[str] = []
    for section in REQUIRED_SECTIONS:
        pattern = re.compile(
            rf"(?ms)^## {re.escape(section)}\s*\n(?P<body>.*?)(?=^## |\Z)"
        )
        match = pattern.search(content)
        if match is None or not match.group("body").strip():
            errors.append(section)

    if LAST_UPDATED_PATTERN.search(content) is None:
        errors.append("Last updated date")

    if errors:
        missing = ", ".join(errors)
        raise MemoryContractError(f"memory.md is missing required content: {missing}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=Path("memory.md"))
    args = parser.parse_args()

    try:
        validate_memory(args.path.read_text(encoding="utf-8"))
    except (OSError, MemoryContractError) as exc:
        parser.exit(status=1, message=f"memory check failed: {exc}\n")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through module entrypoint
    raise SystemExit(main())
