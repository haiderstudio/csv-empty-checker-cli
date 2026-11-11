"""csv-empty-checker-cli: check CSV files for empty rows and empty cells, fail CI when any are found.

Reads one or more CSV files (or folders of them), and reports every
empty row and every empty cell with the file and the line number.
An empty row is a blank line (no cells at all) or a row where every
cell is empty. An empty cell is a cell that is empty or holds only
whitespace, including a quoted empty string ("" in the file).
Report-only: it never rewrites a file. Exit 0 when every file is
clean, 1 when any empty row or cell is found, 2 for a usage error.

Quoted fields are read the way the csv module parses them, so a comma
inside quotes is part of one field, not a new column. A file with a
header and no empty rows or cells passes. A file with no rows at all
is reported, because an empty file has nothing to import.
"""

import argparse
import csv
import fnmatch
import io
import json
import os
import sys
from pathlib import Path

__version__ = "1.0.0"

CSV_SUFFIX = ".csv"


class Problem:
    """One problem in one file: path, line number, plain reason."""

    def __init__(self, path, line, reason):
        self.path = path
        self.line = line
        self.reason = reason

    def text(self):
        return f"{self.path}:{self.line}: {self.reason}"

    def as_dict(self):
        return {"file": self.path, "line": self.line, "reason": self.reason}


def is_empty_cell(cell):
    """True when a cell holds nothing but whitespace (or nothing)."""
    return cell.strip() == ""


def check_text(text, path, delimiter=","):
    """Check one CSV document given as text. Returns a list of Problems."""
    problems = []
    nul_lines = set()
    for lineno, line in enumerate(text.splitlines(), start=1):
        if "\x00" in line:
            nul_lines.add(lineno)
            problems.append(Problem(
                path,
                lineno,
                "cannot parse CSV: line contains NUL",
            ))
    reader = csv.reader(io.StringIO(text, newline=""),
                        delimiter=delimiter, strict=True)
    rows = 0
    try:
        for row in reader:
            rows += 1
            if row == []:
                problems.append(Problem(
                    path,
                    reader.line_num,
                    "empty row (no cells)",
                ))
                continue
            if all(is_empty_cell(cell) for cell in row):
                problems.append(Problem(
                    path,
                    reader.line_num,
                    "empty row (every cell is empty)",
                ))
                continue
            for index, cell in enumerate(row):
                if is_empty_cell(cell):
                    problems.append(Problem(
                        path,
                        reader.line_num,
                        f"empty cell in column {index + 1}",
                    ))
    except csv.Error as exc:
        if "NUL" not in str(exc) or reader.line_num not in nul_lines:
            problems.append(Problem(
                path,
                reader.line_num,
                f"cannot parse CSV: {exc}",
            ))
    if rows == 0:
        problems.append(Problem(path, 1, "empty file (no rows)"))
    return problems


def check_file(path, delimiter=","):
    """Check one CSV file on disk. Returns a list of Problems."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [Problem(str(path), 0,
                        f"cannot read file: {exc.strerror or exc}")]
    return check_text(text, str(path), delimiter)


def is_excluded(name, patterns):
    """True when a file name matches any --exclude glob pattern."""
    return any(fnmatch.fnmatchcase(name, pattern)
               for pattern in patterns)


def collect_files(paths, recursive=True, exclude=()):
    """Gather CSV files from the given paths.

    A file passed directly is always checked, even without a .csv
    extension and even if it matches an --exclude pattern. A folder
    contributes its .csv files (recursively unless --no-recursive),
    skipping .git and __pycache__ folders, never following directory
    links. Returns (files, missing) with files sorted and deduplicated.
    """
    files = []
    missing = []
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            missing.append(raw)
            continue
        if path.is_file():
            files.append(str(path))
            continue
        for root, dirs, names in os.walk(path):
            dirs[:] = sorted(
                name for name in dirs
                if name not in (".git", "__pycache__")
                and not os.path.islink(os.path.join(root, name))
            )
            if not recursive:
                dirs[:] = []
            for name in sorted(names):
                if not name.lower().endswith(CSV_SUFFIX):
                    continue
                if is_excluded(name, exclude):
                    continue
                files.append(str(Path(root) / name))
    return sorted(set(files)), missing


def build_parser():
    parser = argparse.ArgumentParser(
        prog="csv_empty_checker",
        description="Check CSV files for empty rows and empty cells.",
    )
    parser.add_argument(
        "paths", nargs="*", metavar="PATH",
        help="CSV file(s) or folder(s) to check",
    )
    parser.add_argument(
        "--delimiter", default=",",
        help="field delimiter (default: ',')",
    )
    parser.add_argument(
        "--exclude", action="append", default=[], metavar="PATTERN",
        help="skip walked files whose name matches this glob "
             "(repeatable; direct files are always checked)",
    )
    parser.add_argument(
        "--no-recursive", action="store_true",
        help="do not walk into subfolders",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="print the result as machine-readable JSON "
             "(the summary goes to standard error)",
    )
    parser.add_argument(
        "--stdin", action="store_true",
        help="read one CSV document from standard input",
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__,
    )
    return parser


def report_text(results, checked, total):
    """Print the plain-text report. Returns the exit code."""
    files_with_problems = sum(1 for _, probs in results if probs)
    for path, problems in results:
        if problems:
            for problem in problems:
                print(f"FAIL {problem.text()}")
        else:
            print(f"{path}: OK")
    if total == 0:
        print(f"OK — {checked} file(s) checked, "
              "no empty rows or cells.")
        return 0
    print(f"Checked {checked} file(s), {total} problem(s) "
          f"in {files_with_problems} file(s).")
    return 1


def report_json(results, checked, total):
    """Print the JSON report. Returns the exit code."""
    files_with_problems = sum(1 for _, probs in results if probs)
    payload = {
        "files": [
            {
                "file": path,
                "problems": [problem.as_dict() for problem in problems],
            }
            for path, problems in results
        ],
        "summary": {
            "checked": checked,
            "files_with_problems": files_with_problems,
            "problems": total,
        },
    }
    print(json.dumps(payload, indent=2))
    print(f"Checked {checked} file(s), {total} problem(s) "
          f"in {files_with_problems} file(s).", file=sys.stderr)
    return 1 if total else 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if len(args.delimiter) != 1:
        parser.error("--delimiter must be a single character")
    if args.stdin:
        if args.paths:
            parser.error("--stdin takes no PATH arguments")
        results = [("<stdin>", check_text(
            sys.stdin.read(), "<stdin>", args.delimiter))]
        checked = 1
    else:
        if not args.paths:
            parser.error("give at least one PATH, or use --stdin")
        files, missing = collect_files(
            args.paths,
            recursive=not args.no_recursive,
            exclude=args.exclude,
        )
        if missing:
            for raw in missing:
                print(f"error: no such file or folder: {raw}",
                      file=sys.stderr)
            return 2
        if not files:
            print("error: no CSV files found", file=sys.stderr)
            return 2
        results = [(path, check_file(path, args.delimiter))
                   for path in files]
        checked = len(files)
    total = sum(len(problems) for _, problems in results)
    if args.json:
        return report_json(results, checked, total)
    return report_text(results, checked, total)


if __name__ == "__main__":
    sys.exit(main())
