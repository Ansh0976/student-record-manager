"""Input validation for student records.

Every function takes raw input (usually a string typed by a user), returns a
cleaned value, and raises ValidationError with a readable message if the input
is not acceptable. Keeping validation separate from the database and the CLI
means it can be tested on its own.
"""

from __future__ import annotations

import re
from typing import Optional

MIN_GRADE = 1
MAX_GRADE = 12

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ValidationError(ValueError):
    """Raised when a field value is not acceptable."""


def validate_name(value: str) -> str:
    """Letters, spaces, apostrophes, hyphens and dots; 2-60 characters."""
    name = " ".join(str(value).split())  # trim and collapse repeated spaces
    if not 2 <= len(name) <= 60:
        raise ValidationError("Name must be between 2 and 60 characters.")
    for ch in name:
        if not (ch.isalpha() or ch in " '.-"):
            raise ValidationError(f"Name contains an invalid character: {ch!r}")
    return name


def validate_roll_number(value: object) -> int:
    """A whole number from 1 to 9999."""
    try:
        roll = int(str(value).strip())
    except ValueError:
        raise ValidationError("Roll number must be a whole number.") from None
    if not 1 <= roll <= 9999:
        raise ValidationError("Roll number must be between 1 and 9999.")
    return roll


def validate_grade(value: object) -> int:
    """School class, 1 to 12."""
    try:
        grade = int(str(value).strip())
    except ValueError:
        raise ValidationError("Grade must be a whole number.") from None
    if not MIN_GRADE <= grade <= MAX_GRADE:
        raise ValidationError(f"Grade must be between {MIN_GRADE} and {MAX_GRADE}.")
    return grade


def validate_section(value: str) -> str:
    """A single letter A-Z, stored upper-case."""
    section = str(value).strip().upper()
    if not (len(section) == 1 and "A" <= section <= "Z"):
        raise ValidationError("Section must be a single letter (A-Z).")
    return section


def validate_email(value: Optional[str]) -> Optional[str]:
    """Optional. Empty input means 'no email'."""
    if value is None or not str(value).strip():
        return None
    email = str(value).strip()
    if len(email) > 254 or not _EMAIL_RE.match(email):
        raise ValidationError("Email address is not valid.")
    return email


def validate_percentage(value: object) -> Optional[float]:
    """Optional. A number from 0 to 100."""
    if value is None or not str(value).strip():
        return None
    try:
        pct = float(str(value).strip())
    except ValueError:
        raise ValidationError("Percentage must be a number.") from None
    if not 0 <= pct <= 100:  # also rejects NaN, since NaN comparisons are False
        raise ValidationError("Percentage must be between 0 and 100.")
    return round(pct, 2)
