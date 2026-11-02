"""Command-line interface."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from typing import List, Optional, Sequence

from .database import (
    DuplicateStudentError,
    Student,
    StudentNotFoundError,
    StudentRepository,
)
from .export import export_csv
from .validation import ValidationError

DEFAULT_DB = "students.db"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="student-manager", description="Manage school student records (SQLite)."
    )
    parser.add_argument("--db", default=DEFAULT_DB, help=f"database file (default: {DEFAULT_DB})")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="add a student")
    add.add_argument("--name", required=True)
    add.add_argument("--roll", required=True, help="roll number")
    add.add_argument("--grade", required=True, help="class, 1-12")
    add.add_argument("--section", required=True, help="single letter")
    add.add_argument("--email")
    add.add_argument("--percentage")

    ls = sub.add_parser("list", help="list students")
    ls.add_argument("--grade")
    ls.add_argument("--section")

    search = sub.add_parser("search", help="search by name or email")
    search.add_argument("term")

    upd = sub.add_parser("update", help="update a student by id")
    upd.add_argument("id", type=int)
    upd.add_argument("--name")
    upd.add_argument("--roll", dest="roll_number")
    upd.add_argument("--grade")
    upd.add_argument("--section")
    upd.add_argument("--email")
    upd.add_argument("--percentage")

    dele = sub.add_parser("delete", help="delete a student by id")
    dele.add_argument("id", type=int)
    dele.add_argument("--yes", action="store_true", help="skip the confirmation prompt")

    exp = sub.add_parser("export", help="export all students to CSV")
    exp.add_argument("path")

    srv = sub.add_parser("serve", help="open the web interface in your browser")
    srv.add_argument("--port", type=int, default=5000)
    srv.add_argument("--host", default="127.0.0.1", help="default is this computer only")

    return parser


def format_table(students: Sequence[Student]) -> str:
    if not students:
        return "No students found."
    header = f"{'ID':>4}  {'Name':<24} {'Class':<6} {'Roll':>5}  {'%':>6}  Email"
    lines = [header, "-" * len(header)]
    for s in students:
        pct = "" if s.percentage is None else f"{s.percentage:.1f}"
        lines.append(
            f"{s.id:>4}  {s.name:<24.24} {f'{s.grade}-{s.section}':<6} "
            f"{s.roll_number:>5}  {pct:>6}  {s.email or ''}"
        )
    lines.append(f"\n{len(students)} student(s)")
    return "\n".join(lines)


def _run(args: argparse.Namespace, repo: StudentRepository) -> int:
    if args.command == "add":
        s = repo.add(args.name, args.roll, args.grade, args.section, args.email, args.percentage)
        print(f"Added student #{s.id}: {s.name} ({s.grade}-{s.section}, roll {s.roll_number})")
    elif args.command == "list":
        print(format_table(repo.list_all(args.grade, args.section)))
    elif args.command == "search":
        print(format_table(repo.search(args.term)))
    elif args.command == "update":
        changes = {
            k: getattr(args, k)
            for k in ("name", "roll_number", "grade", "section", "email", "percentage")
            if getattr(args, k) is not None
        }
        s = repo.update(args.id, **changes)
        print(f"Updated student #{s.id}: {s.name} ({s.grade}-{s.section}, roll {s.roll_number})")
    elif args.command == "delete":
        s = repo.get(args.id)
        if not args.yes:
            answer = input(f"Delete {s.name} ({s.grade}-{s.section}, roll {s.roll_number})? [y/N] ")
            if answer.strip().lower() != "y":
                print("Cancelled.")
                return 0
        repo.delete(args.id)
        print(f"Deleted student #{args.id}.")
    elif args.command == "export":
        n = export_csv(repo.list_all(), args.path)
        print(f"Exported {n} student(s) to {args.path}")
    return 0


def _serve(args: argparse.Namespace) -> int:
    try:
        from .web import create_app
    except ImportError:
        print(
            'The web interface needs Flask. Install it with: pip install -e ".[web]"',
            file=sys.stderr,
        )
        return 1
    try:
        StudentRepository(args.db).close()  # fail early with a clear message
    except sqlite3.Error as err:
        print(f"Cannot open database '{args.db}': {err}", file=sys.stderr)
        return 1
    print(f"Student register running at http://{args.host}:{args.port}  (Ctrl+C to stop)")
    create_app(args.db).run(host=args.host, port=args.port, debug=False)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "serve":
        return _serve(args)
    try:
        with StudentRepository(args.db) as repo:
            return _run(args, repo)
    except (ValidationError, DuplicateStudentError, StudentNotFoundError, ValueError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1
    except sqlite3.Error as err:
        print(f"Database error: {err}", file=sys.stderr)
        return 1
    except OSError as err:
        print(f"File error: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
