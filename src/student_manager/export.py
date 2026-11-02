"""CSV export."""

from __future__ import annotations

import csv
from typing import Iterable

from .database import Student

HEADER = ["id", "name", "roll_number", "grade", "section", "email", "percentage"]

# Spreadsheet programs treat cells starting with these characters as formulas.
_FORMULA_PREFIXES = ("=", "+", "-", "@")


def _safe_cell(value: object) -> object:
    """Neutralise CSV/formula injection by prefixing risky text with a quote."""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return "" if value is None else value


def export_csv(students: Iterable[Student], path: str) -> int:
    """Write students to a CSV file. Returns the number of rows written."""
    count = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        for s in students:
            writer.writerow(
                [
                    _safe_cell(v)
                    for v in (s.id, s.name, s.roll_number, s.grade, s.section, s.email, s.percentage)
                ]
            )
            count += 1
    return count
