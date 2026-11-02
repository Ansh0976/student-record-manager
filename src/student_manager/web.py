"""Web interface: a small JSON API plus a single-page front end.

Needs Flask (`pip install -e ".[web]"`). It reuses StudentRepository, so the
validation and database rules are exactly the same as in the command line.
"""

from __future__ import annotations

import io
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Flask, Response, jsonify, request, send_from_directory

from .database import (
    DuplicateStudentError,
    StudentNotFoundError,
    StudentRepository,
)
from .export import write_csv
from .validation import ValidationError

STATIC_DIR = Path(__file__).parent / "static"

_FIELDS = ("name", "roll_number", "grade", "section", "email", "percentage")
_REQUIRED = ("name", "roll_number", "grade", "section")


def _read_json_body() -> Dict[str, Any]:
    if not request.is_json:
        raise ValidationError("Send the data as JSON.")
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object.")
    for key, value in data.items():
        if isinstance(value, (dict, list, bool)):
            raise ValidationError(f"'{key}' has an invalid value.")
    return data


def create_app(db_path: str = "students.db") -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024  # reject oversized request bodies

    def repo() -> StudentRepository:
        # One short-lived connection per request keeps SQLite thread-safe.
        return StudentRepository(db_path)

    @app.errorhandler(ValueError)  # also covers ValidationError
    def bad_request(err: Exception):
        return jsonify(error=str(err)), 400

    @app.errorhandler(DuplicateStudentError)
    def conflict(err: Exception):
        return jsonify(error=str(err)), 409

    @app.errorhandler(StudentNotFoundError)
    def not_found(err: Exception):
        return jsonify(error=str(err)), 404

    @app.errorhandler(413)
    def too_large(_err: Exception):
        return jsonify(error="Request is too large."), 413

    @app.get("/")
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    @app.get("/api/students")
    def list_students():
        grade: Optional[str] = request.args.get("grade") or None
        section: Optional[str] = request.args.get("section") or None
        term = (request.args.get("q") or "").strip()
        with repo() as r:
            students = r.search(term) if term else r.list_all()
            if grade is not None:
                wanted = r.list_all(grade=grade, section=section)
                keep = {s.id for s in wanted}
                students = [s for s in students if s.id in keep]
            elif section is not None:
                students = [s for s in students if s.section == section.strip().upper()]
        return jsonify([asdict(s) for s in students])

    @app.post("/api/students")
    def add_student():
        data = _read_json_body()
        missing = [k for k in _REQUIRED if data.get(k) in (None, "")]
        if missing:
            raise ValidationError(f"Missing required field(s): {', '.join(missing)}.")
        with repo() as r:
            s = r.add(**{k: data.get(k) for k in _FIELDS})
        return jsonify(asdict(s)), 201

    @app.put("/api/students/<int:student_id>")
    def update_student(student_id: int):
        data = _read_json_body()
        changes = {k: data[k] for k in _FIELDS if k in data}
        for key in _REQUIRED:
            if key in changes and changes[key] in (None, ""):
                raise ValidationError(f"'{key}' cannot be empty.")
        with repo() as r:
            s = r.update(student_id, **changes)
        return jsonify(asdict(s))

    @app.delete("/api/students/<int:student_id>")
    def delete_student(student_id: int):
        with repo() as r:
            r.delete(student_id)
        return "", 204

    @app.get("/api/export.csv")
    def export():
        buf = io.StringIO()
        with repo() as r:
            write_csv(r.list_all(), buf)
        return Response(
            buf.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=students.csv"},
        )

    return app
