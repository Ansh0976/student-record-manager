import csv

import pytest

from student_manager.cli import main
from student_manager.database import Student
from student_manager.export import HEADER, _safe_cell, export_csv


def make_student(**kw):
    base = dict(id=1, name="Asha Verma", roll_number=1, grade=10, section="A",
                email="asha@example.com", percentage=88.5)
    base.update(kw)
    return Student(**base)


def test_export_csv_roundtrip(tmp_path):
    path = tmp_path / "out.csv"
    n = export_csv([make_student(), make_student(id=2, name="Ravi Kumar", email=None, percentage=None)], str(path))
    assert n == 2
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == HEADER
    assert rows[1] == ["1", "Asha Verma", "1", "10", "A", "asha@example.com", "88.5"]
    assert rows[2][5:] == ["", ""]  # missing values become empty cells


@pytest.mark.parametrize("risky", ["=1+1", "+cmd", "-2", "@SUM(A1)"])
def test_formula_injection_neutralised(risky):
    assert _safe_cell(risky) == "'" + risky


def test_normal_values_untouched():
    assert _safe_cell("hello") == "hello"
    assert _safe_cell(5) == 5
    assert _safe_cell(None) == ""


@pytest.fixture
def db(tmp_path):
    return str(tmp_path / "cli.db")


def run(db, *args):
    return main(["--db", db, *args])


def test_cli_full_flow(db, capsys, tmp_path):
    assert run(db, "add", "--name", "Asha Verma", "--roll", "1", "--grade", "10",
               "--section", "a", "--percentage", "88.5") == 0
    assert "Added student #1" in capsys.readouterr().out

    assert run(db, "list") == 0
    out = capsys.readouterr().out
    assert "Asha Verma" in out and "10-A" in out and "1 student(s)" in out

    assert run(db, "search", "asha") == 0
    assert "Asha Verma" in capsys.readouterr().out

    assert run(db, "update", "1", "--percentage", "91") == 0
    assert "Updated student #1" in capsys.readouterr().out

    csv_path = str(tmp_path / "x.csv")
    assert run(db, "export", csv_path) == 0
    assert "Exported 1 student(s)" in capsys.readouterr().out

    assert run(db, "delete", "1", "--yes") == 0
    assert run(db, "list") == 0
    assert "No students found." in capsys.readouterr().out


def test_cli_reports_errors_without_traceback(db, capsys):
    assert run(db, "add", "--name", "A", "--roll", "1", "--grade", "10", "--section", "A") == 1
    assert "Error:" in capsys.readouterr().err
    assert run(db, "delete", "99", "--yes") == 1
    assert "No student with id 99" in capsys.readouterr().err


def test_cli_duplicate_error(db, capsys):
    args = ("add", "--name", "Asha Verma", "--roll", "1", "--grade", "10", "--section", "A")
    assert run(db, *args) == 0
    capsys.readouterr()
    assert run(db, *args) == 1
    assert "already exists" in capsys.readouterr().err


def test_cli_delete_cancelled(db, capsys, monkeypatch):
    run(db, "add", "--name", "Asha Verma", "--roll", "1", "--grade", "10", "--section", "A")
    capsys.readouterr()
    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert run(db, "delete", "1") == 0
    assert "Cancelled." in capsys.readouterr().out
    run(db, "list")
    assert "Asha Verma" in capsys.readouterr().out
