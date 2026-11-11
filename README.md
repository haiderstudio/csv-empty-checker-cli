# csv-empty-checker-cli

Check CSV files for empty rows and empty cells, fail CI when any are found.

[![CI](https://github.com/haiderstudio/csv-empty-checker-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/haiderstudio/csv-empty-checker-cli/actions/workflows/ci.yml) [![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE)

## What it does

`csv_empty_checker` reads each CSV file you point it at and
reports every empty row and every empty cell, with the file and
the line number:

- An empty row is a blank line (no cells at all) or a row where
  every cell is empty — a line of bare commas, for example. An
  empty row shifts everything after it or breaks an import, and
  the file still looks fine at a glance. Anyone shipping CSV
  data files needs this: a stray blank line in a spreadsheet
  export is the classic silent break.
- An empty cell is a cell that is empty or holds only
  whitespace, including a quoted empty string (`""` in the
  file). A missing value reads as NaN in pandas and downstream
  code quietly computes the wrong thing — a total that is off,
  a name that is blank. This tool reports each empty cell with
  its column number, so you can find it at once.
- It exits 1 when any empty row or cell is found, so it can fail
  a CI run. A clean folder exits 0.
- Fields are read the way Python's `csv` module parses them, so
  a comma inside quotes is part of one field, not a new column
  — the `good.csv` example has a quoted `"Carol, Jr."` name
  and passes clean.
- CSV files come from the command line (one or more), or from a
  folder walk: every `.csv` file under a folder, recursively by
  default (`--no-recursive` stops at the top level). `.git` and
  `__pycache__` folders are never walked, and directory links
  are never followed, so a link cycle cannot loop the check.
- `--delimiter` sets the field separator, for example
  `--delimiter ';'` for semicolon files. A file checked with
  the wrong delimiter is not an error — it is just checked as
  one-field rows — so pick the delimiter your files use.
- `--exclude PATTERN` skips walked files by glob, for example
  `--exclude 'draft-*'`. It can be repeated. A file passed
  directly on the command line is always checked, even if it
  matches an exclude pattern and even if it has no `.csv`
  extension.
- `--stdin` reads one CSV document from standard input.
- `--json` prints the result as machine-readable JSON (the
  summary goes to standard error, so standard output stays
  clean JSON).
- It is report-only and runs fully offline: it never edits a
  file, sends nothing anywhere, and needs no API key. Python
  standard library only — the `csv` module does the parsing.

## What it does NOT do

- It does not check column counts — that is repo #58's
  `csv-column-count-checker-cli`. A row with the wrong number
  of columns but no empty cells passes here.
- It does not check the header row's names or duplicates —
  that is repo #40's `csv-header-checker-cli`. An empty header
  cell is reported here (it is an empty cell), but a missing
  or misspelled header name is not this tool's job.
- It does not fill in, delete, or fix empty rows or cells.
  An empty cell is reported; deciding what belongs there is
  your job.
- It does not check fully-empty COLUMNS — a column that is
  empty in every row but has a header is a different question
  from scattered empty cells. A row where every cell is empty
  is reported as an empty row; a column where every data cell
  is empty is reported cell by cell.

## Who it is for

Anyone who ships CSV data files and wants them clean before
they are imported: a data analyst checking a spreadsheet
export, a developer adding a CI step that fails the build
when a data file has a blank row or a missing value, or
anyone tidying a folder of CSVs before they go into a
database. An empty row or cell is invisible in the file
itself — this catches it before the import does.

## How this differs from similar tools

The exact name `csv-empty-checker-cli` matches 0
repositories on GitHub (checked Nov 10, 2026), and the
wider field is small: `csv empty checker` matches 4
repositories. The top ones are
deadpyxel/csv-column-checker, 0 stars — it checks for a
totally empty COLUMN (a different job from empty rows and
scattered empty cells) — and mrrishit909/csv-quality-checker,
0 stars — a Java data-quality checker where empties are one
check among several (types, duplicates, outliers), with no
CI claim. The rest are noise (a database security audit, a
Sudoku solver). None of them is a tested Python CLI that
checks empty rows and empty cells as its one job, reports
each with file and line, and exits 1 for CI. This tool does
that one job: a Python standard-library-only CLI that checks
CSV files for empty rows and empty cells — no install beyond
Python, no website, no network.

## Install

Python standard library only — no packages to download. You need
Python 3.8 or newer. Clone the repo and run it in place:

```
git clone https://github.com/haiderstudio/csv-empty-checker-cli.git
cd csv-empty-checker-cli
python3 src/csv_empty_checker.py examples/good.csv
```

```
examples/good.csv: OK
OK — 1 file(s) checked, no empty rows or cells.
```

## Usage

Check one clean file:

```
python3 src/csv_empty_checker.py examples/good.csv
```

```
examples/good.csv: OK
OK — 1 file(s) checked, no empty rows or cells.
```

Check a file with empty cells (line 3 has an empty name, line 4
an empty score, line 5 a quoted empty name):

```
python3 src/csv_empty_checker.py examples/empty-cells.csv
```

```
FAIL examples/empty-cells.csv:3: empty cell in column 2
FAIL examples/empty-cells.csv:4: empty cell in column 3
FAIL examples/empty-cells.csv:5: empty cell in column 2
Checked 1 file(s), 3 problem(s) in 1 file(s).
```

Check a file with empty rows (a blank line, then a line of bare
commas):

```
python3 src/csv_empty_checker.py examples/empty-rows.csv
```

```
FAIL examples/empty-rows.csv:3: empty row (no cells)
FAIL examples/empty-rows.csv:5: empty row (every cell is empty)
Checked 1 file(s), 2 problem(s) in 1 file(s).
```

Check a file with an empty header cell:

```
python3 src/csv_empty_checker.py examples/header-gap.csv
```

```
FAIL examples/header-gap.csv:1: empty cell in column 2
Checked 1 file(s), 1 problem(s) in 1 file(s).
```

Check a semicolon file — first without the flag, then with it.
Without `--delimiter ';'` the lines are read as single fields
and nothing looks empty:

```
python3 src/csv_empty_checker.py examples/semicolon.csv
```

```
examples/semicolon.csv: OK
OK — 1 file(s) checked, no empty rows or cells.
```

```
python3 src/csv_empty_checker.py --delimiter ';' examples/semicolon.csv
```

```
FAIL examples/semicolon.csv:3: empty cell in column 2
Checked 1 file(s), 1 problem(s) in 1 file(s).
```

Check a whole folder:

```
python3 src/csv_empty_checker.py examples/
```

```
FAIL examples/empty-cells.csv:3: empty cell in column 2
FAIL examples/empty-cells.csv:4: empty cell in column 3
FAIL examples/empty-cells.csv:5: empty cell in column 2
FAIL examples/empty-rows.csv:3: empty row (no cells)
FAIL examples/empty-rows.csv:5: empty row (every cell is empty)
examples/good.csv: OK
FAIL examples/header-gap.csv:1: empty cell in column 2
examples/semicolon.csv: OK
Checked 5 file(s), 6 problem(s) in 3 file(s).
```

Check one document from standard input:

```
python3 src/csv_empty_checker.py --stdin < examples/empty-rows.csv
```

```
FAIL <stdin>:3: empty row (no cells)
FAIL <stdin>:5: empty row (every cell is empty)
Checked 1 file(s), 2 problem(s) in 1 file(s).
```

Machine-readable output with `--json` (the summary goes to
standard error, so standard output stays clean JSON):

```
python3 src/csv_empty_checker.py --json examples/empty-cells.csv
```

```
{
  "files": [
    {
      "file": "examples/empty-cells.csv",
      "problems": [
        {
          "file": "examples/empty-cells.csv",
          "line": 3,
          "reason": "empty cell in column 2"
        },
        {
          "file": "examples/empty-cells.csv",
          "line": 4,
          "reason": "empty cell in column 3"
        },
        {
          "file": "examples/empty-cells.csv",
          "line": 5,
          "reason": "empty cell in column 2"
        }
      ]
    }
  ],
  "summary": {
    "checked": 1,
    "files_with_problems": 1,
    "problems": 3
  }
}
```

Exit codes: 0 when every checked file is clean, 1 when any
empty row or cell is found, 2 for a usage problem (no files
given, a bad flag, a bad `--delimiter` value, or a missing
file or folder).

## Examples

### 1. A folder of data files, default comma delimiter

`examples/` holds five CSV files. Two pass, three fail — a
blank line and a bare-commas row, three empty cells, and an
empty header cell:

```
python3 src/csv_empty_checker.py examples/
```

```
FAIL examples/empty-cells.csv:3: empty cell in column 2
FAIL examples/empty-cells.csv:4: empty cell in column 3
FAIL examples/empty-cells.csv:5: empty cell in column 2
FAIL examples/empty-rows.csv:3: empty row (no cells)
FAIL examples/empty-rows.csv:5: empty row (every cell is empty)
examples/good.csv: OK
FAIL examples/header-gap.csv:1: empty cell in column 2
examples/semicolon.csv: OK
Checked 5 file(s), 6 problem(s) in 3 file(s).
```

### 2. The semicolon file, checked properly

```
python3 src/csv_empty_checker.py --delimiter ';' examples/semicolon.csv
```

```
FAIL examples/semicolon.csv:3: empty cell in column 2
Checked 1 file(s), 1 problem(s) in 1 file(s).
```

### 3. The bundled examples, all at once

```
sh examples/run-example.sh
```

The script checks the whole `examples/` folder (fail, on
purpose — it picks up the empty rows, the empty cells, and
the empty header cell). Its full output is in
`examples/sample-output.md`, ending with `Checked 5 file(s),
6 problem(s) in 3 file(s).` The failing run exits 1, which
is the expected result — the script ends with exit 0 so it
can be run as a demo.

## How it is tested

Tests, standard library `unittest` only, no packages to install:

```
python3 tests/test_csv_empty_checker.py
```

The tests cover: empty rows (blank lines, lines of bare
commas, a row of whitespace-only cells, a blank line at the
end of a file, CRLF line endings), empty cells (middle,
first, and last column, the header row, a quoted empty
string, a whitespace-only cell, a quoted comma that is not
an empty cell), clean files (quoted fields with commas,
multi-line quoted fields, a header-only file), edge cases
(an empty file, a file with only a header, NUL bytes,
a malformed quoted field, a custom delimiter, a
tab-delimited file), file collection (a good file, a
missing path, a folder walk, `.git` skipped,
`--no-recursive`, `--exclude`, a direct file checked even
without a `.csv` extension and even if excluded, an empty
folder, uppercase `.CSV` extensions), the CLI (exit 0/1/2,
each flag, `--stdin` good and bad, `--json` output,
`--version`, bad flags, a bad delimiter, missing paths, a
folder summary count, and every bundled example file read
back with its expected problems), the bundled examples
(sample output compared byte-for-byte against a fresh run,
and the README-quoted outputs checked against it), and
hygiene checks (no placeholder text, no absolute paths,
stdlib imports only, `.env` first in `.gitignore`, CI file
runs the test file).

## Contributing

Small, focused improvements are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — see [LICENSE](LICENSE).

## Original work

This tool was written from scratch for this repo. The idea
of checking CSV files for empty rows and cells is not new —
the similar tools named above (the 0-star empty-column
checker, the 0-star Java data-quality checker) are listed
in "How this differs" — but every line of code here is
original, and the tool builds on nothing but Python's
standard library.
