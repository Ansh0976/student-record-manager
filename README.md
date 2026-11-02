# Student Record Manager

A small command-line tool for managing school student records, backed by SQLite.

This started as a school project written in Python. This repository is a from-scratch rewrite of it, focused on structure, input validation and tests rather than new features.

## Features

- Add, list, search, update and delete student records
- Records are stored in a local SQLite database, so they persist between runs
- Input validation on every field, with clear error messages
- Roll numbers are unique within a class and section
- Filter the list by grade and section
- Export all records to CSV
- Standard library only, no runtime dependencies

## Install

Requires Python 3.9 or newer.

```bash
git clone https://github.com/Ansh0976/student-record-manager.git
cd student-record-manager
pip install -e .
```

To run the tests as well: `pip install -e ".[dev]"`.

## Usage

```bash
student-manager add --name "Asha Verma" --roll 1 --grade 10 --section A --email asha@example.com --percentage 88.5
student-manager add --name "Ravi Kumar" --roll 2 --grade 10 --section A --percentage 72
student-manager list
student-manager list --grade 10 --section A
student-manager search ravi
student-manager update 2 --percentage 75
student-manager delete 2            # asks for confirmation; add --yes to skip
student-manager export students.csv
```

Without installing, `python -m student_manager ...` works from the repository root if `src` is on `PYTHONPATH`.

By default the database is `students.db` in the current folder. Use `--db path/to/file.db` to choose another one.

Example output:

```
  ID  Name                     Class   Roll       %  Email
----------------------------------------------------------
   1  Asha Verma               10-A       1    88.5  asha@example.com
   2  Ravi Kumar               10-A       2    72.0
   3  Meera Joshi              10-B       1

3 student(s)
```

Errors are reported as a message with exit code 1, not a traceback:

```
Error: Roll number 1 already exists in grade 10-A.
Error: Grade must be between 1 and 12.
```

## Project structure

```
src/student_manager/
    validation.py   # one function per field; returns a cleaned value or raises ValidationError
    database.py     # StudentRepository: all SQL lives here
    export.py       # CSV export
    cli.py          # argparse commands; no SQL and no validation rules
tests/              # pytest suite
```

Keeping validation, storage and the interface in separate modules means each can be tested without the others. The tests use an in-memory SQLite database, so they never touch real data.

## Design decisions

- **Parameterised SQL.** Every query passes values through `?` placeholders instead of building strings, so input like `' OR '1'='1` is treated as plain text. There is a test for this.
- **Whitelisted columns on update.** The `UPDATE` statement builds its column list from a fixed dictionary of known fields, never from user input.
- **Constraints in the database too.** The schema has `CHECK` constraints and a `UNIQUE (grade, section, roll_number)` rule, so bad data is rejected even if the Python validation is bypassed.
- **LIKE wildcards escaped in search.** Searching for `%` or `_` matches those characters literally instead of matching everything.
- **CSV formula injection.** Spreadsheet programs run cells that start with `=`, `+`, `-` or `@` as formulas. The exporter prefixes such cells with a quote.

## Testing

```bash
pytest
```

The suite covers validation edge cases, duplicate handling, update and delete behaviour, persistence on disk, CSV output and the CLI end to end.

## Limitations

- Single-user. SQLite handles one writer at a time and there is no login or access control.
- No authentication, so anyone who can run the tool can change the data.
- No pagination: `list` prints every matching record.
- Names accept letters, spaces, `'`, `-` and `.` only, which may reject some real names.
- Percentage is a single number per student, not a per-subject marks model.
- There is no schema migration. Changing the table would need a migration step.

## Possible improvements

- Per-subject marks in a separate table, with computed averages and ranks
- CSV import with row-level error reports
- An interactive menu mode
- A small web interface using the same repository layer

## Licence

MIT. See [LICENSE](LICENSE).
