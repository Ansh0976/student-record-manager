"""SQLite storage for student records."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import List, Optional

from .validation import (
    validate_email,
    validate_grade,
    validate_name,
    validate_percentage,
    validate_roll_number,
    validate_section,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    roll_number INTEGER NOT NULL,
    grade       INTEGER NOT NULL CHECK (grade BETWEEN 1 AND 12),
    section     TEXT    NOT NULL,
    email       TEXT,
    percentage  REAL    CHECK (percentage IS NULL OR percentage BETWEEN 0 AND 100),
    UNIQUE (grade, section, roll_number)
);
"""

# Maps a field name to the function that validates it. Only these fields can
# be updated, so a column name is never built from raw user input.
_FIELD_VALIDATORS = {
    "name": validate_name,
    "roll_number": validate_roll_number,
    "grade": validate_grade,
    "section": validate_section,
    "email": validate_email,
    "percentage": validate_percentage,
}


class DuplicateStudentError(Exception):
    """A student with the same grade, section and roll number already exists."""


class StudentNotFoundError(Exception):
    """No student exists with the given id."""


@dataclass(frozen=True)
class Student:
    id: int
    name: str
    roll_number: int
    grade: int
    section: str
    email: Optional[str]
    percentage: Optional[float]


def _row_to_student(row: sqlite3.Row) -> Student:
    return Student(**dict(row))


class StudentRepository:
    """All database access lives here. Use ':memory:' as the path for tests."""

    def __init__(self, path: str = "students.db") -> None:
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "StudentRepository":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def add(
        self,
        name: str,
        roll_number: object,
        grade: object,
        section: str,
        email: Optional[str] = None,
        percentage: object = None,
    ) -> Student:
        values = (
            validate_name(name),
            validate_roll_number(roll_number),
            validate_grade(grade),
            validate_section(section),
            validate_email(email),
            validate_percentage(percentage),
        )
        try:
            # '?' placeholders let sqlite3 handle quoting, which prevents SQL injection.
            cur = self._conn.execute(
                "INSERT INTO students "
                "(name, roll_number, grade, section, email, percentage) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                values,
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            self._conn.rollback()
            raise DuplicateStudentError(
                f"Roll number {values[1]} already exists in grade {values[2]}-{values[3]}."
            ) from None
        return self.get(cur.lastrowid)

    def get(self, student_id: int) -> Student:
        row = self._conn.execute(
            "SELECT * FROM students WHERE id = ?", (student_id,)
        ).fetchone()
        if row is None:
            raise StudentNotFoundError(f"No student with id {student_id}.")
        return _row_to_student(row)

    def list_all(
        self, grade: Optional[int] = None, section: Optional[str] = None
    ) -> List[Student]:
        query = "SELECT * FROM students"
        clauses, params = [], []
        if grade is not None:
            clauses.append("grade = ?")
            params.append(validate_grade(grade))
        if section is not None:
            clauses.append("section = ?")
            params.append(validate_section(section))
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY grade, section, roll_number"
        return [_row_to_student(r) for r in self._conn.execute(query, params)]

    def search(self, term: str) -> List[Student]:
        """Case-insensitive match on name or email."""
        # Escape LIKE wildcards so searching for '%' or '_' matches literally.
        escaped = term.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        rows = self._conn.execute(
            "SELECT * FROM students "
            "WHERE name LIKE ? ESCAPE '\\' OR email LIKE ? ESCAPE '\\' "
            "ORDER BY grade, section, roll_number",
            (pattern, pattern),
        )
        return [_row_to_student(r) for r in rows]

    def update(self, student_id: int, **changes: object) -> Student:
        self.get(student_id)  # raises StudentNotFoundError if missing
        if not changes:
            raise ValueError("No fields to update.")
        unknown = set(changes) - set(_FIELD_VALIDATORS)
        if unknown:
            raise ValueError(f"Unknown field(s): {', '.join(sorted(unknown))}")
        cleaned = {k: _FIELD_VALIDATORS[k](v) for k, v in changes.items()}
        assignments = ", ".join(f"{col} = ?" for col in cleaned)  # col names come from our whitelist
        try:
            self._conn.execute(
                f"UPDATE students SET {assignments} WHERE id = ?",
                (*cleaned.values(), student_id),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            self._conn.rollback()
            raise DuplicateStudentError(
                "Another student already has that grade, section and roll number."
            ) from None
        return self.get(student_id)

    def delete(self, student_id: int) -> None:
        cur = self._conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
        self._conn.commit()
        if cur.rowcount == 0:
            raise StudentNotFoundError(f"No student with id {student_id}.")

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
