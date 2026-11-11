"""Tests for csv_empty_checker: empty rows, empty cells, CLI, examples, hygiene."""

import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import csv_empty_checker as checker

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "csv_empty_checker.py"
EXAMPLES = ROOT / "examples"
README = ROOT / "README.md"


def problems(text, delimiter=","):
    return [(p.path, p.line, p.reason)
            for p in checker.check_text(text, "t.csv", delimiter)]


def reasons(text, delimiter=","):
    return [(p.line, p.reason)
            for p in checker.check_text(text, "t.csv", delimiter)]


class TestEmptyRows(unittest.TestCase):
    def test_blank_line_is_empty_row(self):
        found = reasons("a,b\n1,2\n\n3,4\n")
        self.assertEqual(found, [(3, "empty row (no cells)")])

    def test_bare_commas_row_is_empty_row(self):
        found = reasons("a,b\n,,\n")
        self.assertEqual(found, [(2, "empty row (every cell is empty)")])

    def test_whitespace_only_row_is_empty_row(self):
        found = reasons("a,b\n  ,  \n")
        self.assertEqual(found, [(2, "empty row (every cell is empty)")])

    def test_single_comma_row_is_empty_row(self):
        found = reasons("a,b\n,\n")
        self.assertEqual(found, [(2, "empty row (every cell is empty)")])

    def test_blank_line_at_end_of_file(self):
        found = reasons("a,b\n1,2\n\n")
        self.assertEqual(found, [(3, "empty row (no cells)")])

    def test_multiple_blank_lines(self):
        found = reasons("a,b\n\n\n1,2\n")
        self.assertEqual(found, [(2, "empty row (no cells)"),
                                 (3, "empty row (no cells)")])

    def test_crlf_blank_line(self):
        found = reasons("a,b\r\n1,2\r\n\r\n3,4\r\n")
        self.assertEqual(found, [(3, "empty row (no cells)")])

    def test_empty_row_reports_once_not_per_cell(self):
        found = reasons("a,b,c\n,,,\n")
        self.assertEqual(len(found), 1)
        self.assertIn("empty row", found[0][1])


class TestEmptyCells(unittest.TestCase):
    def test_empty_middle_cell(self):
        found = reasons("a,b,c\n1,,3\n")
        self.assertEqual(found, [(2, "empty cell in column 2")])

    def test_empty_first_cell(self):
        found = reasons("a,b\n,2\n")
        self.assertEqual(found, [(2, "empty cell in column 1")])

    def test_empty_last_cell(self):
        found = reasons("a,b\n1,\n")
        self.assertEqual(found, [(2, "empty cell in column 2")])

    def test_empty_header_cell(self):
        found = reasons("a,,c\n1,2,3\n")
        self.assertEqual(found, [(1, "empty cell in column 2")])

    def test_quoted_empty_string_is_empty_cell(self):
        found = reasons('a,b\n1,""\n')
        self.assertEqual(found, [(2, "empty cell in column 2")])

    def test_whitespace_only_cell_is_empty(self):
        found = reasons("a,b\n1,   \n")
        self.assertEqual(found, [(2, "empty cell in column 2")])

    def test_quoted_comma_is_not_empty(self):
        self.assertEqual(reasons('a,b\n"1,5",2\n'), [])

    def test_cell_with_zero_is_not_empty(self):
        self.assertEqual(reasons("a,b\n0,0\n"), [])

    def test_several_empty_cells_one_row(self):
        found = reasons("a,b,c\n,,3\n")
        self.assertEqual(found, [(2, "empty cell in column 1"),
                                 (2, "empty cell in column 2")])

    def test_header_only_file_passes(self):
        self.assertEqual(reasons("a,b,c\n"), [])

    def test_row_after_empty_row_still_checked(self):
        found = reasons("a,b\n\n1,\n")
        self.assertEqual(found, [(2, "empty row (no cells)"),
                                 (3, "empty cell in column 2")])


class TestCleanFiles(unittest.TestCase):
    def test_clean_file_passes(self):
        self.assertEqual(reasons("id,name,score\n1,Alice,90\n"), [])

    def test_quoted_field_with_comma_passes(self):
        self.assertEqual(
            reasons('id,name\n1,"Carol, Jr."\n'), [])

    def test_multiline_quoted_field(self):
        self.assertEqual(
            reasons('a,b\n"line one\nline two",2\n'), [])

    def test_ragged_rows_without_empties_pass(self):
        # Column counts are repo #58's job, not this one.
        self.assertEqual(reasons("a,b\n1,2,3\n"), [])


class TestEdgeCases(unittest.TestCase):
    def test_empty_file_reported(self):
        found = reasons("")
        self.assertEqual(found, [(1, "empty file (no rows)")])

    def test_only_newline_file_is_empty_row(self):
        found = reasons("\n")
        self.assertEqual(found, [(1, "empty row (no cells)")])

    def test_nul_byte_reported_once(self):
        found = reasons("a,b\n1,\x002\n")
        self.assertEqual(len(found), 1)
        self.assertIn("NUL", found[0][1])

    def test_malformed_quoted_field(self):
        found = reasons('a,b\n1,"unclosed\n')
        self.assertEqual(len(found), 1)
        self.assertIn("cannot parse CSV", found[0][1])

    def test_custom_delimiter(self):
        found = reasons("a;b\n1;;3\n", delimiter=";")
        self.assertEqual(found, [(2, "empty cell in column 2")])

    def test_tab_delimiter(self):
        found = reasons("a\tb\n1\t\n", delimiter="\t")
        self.assertEqual(found, [(2, "empty cell in column 2")])

    def test_problem_text_format(self):
        problem = checker.check_text("a,b\n,2\n", "f.csv")[0]
        self.assertEqual(problem.text(),
                         "f.csv:2: empty cell in column 1")

    def test_problem_as_dict(self):
        problem = checker.check_text("a,b\n,2\n", "f.csv")[0]
        self.assertEqual(problem.as_dict(), {
            "file": "f.csv", "line": 2,
            "reason": "empty cell in column 1",
        })


class TestCheckFile(unittest.TestCase):
    def test_unreadable_path(self):
        found = checker.check_file("/nonexistent-dir-xyz/f.csv")
        self.assertEqual(len(found), 1)
        self.assertIn("cannot read file", found[0].reason)

    def test_file_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.csv"
            path.write_text("a,b\n,2\n")
            found = checker.check_file(str(path))
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0].line, 2)


class TestCollection(unittest.TestCase):
    def test_folder_walk_finds_csv_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.csv").write_text("a,b\n1,2\n")
            (root / "b.txt").write_text("a,b\n,2\n")
            (root / "sub").mkdir()
            (root / "sub" / "c.csv").write_text("a,b\n,2\n")
            files, missing = checker.collect_files([str(root)])
            self.assertEqual(missing, [])
            self.assertEqual(
                files, [str(root / "a.csv"), str(root / "sub" / "c.csv")])

    def test_git_folder_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            (root / ".git" / "x.csv").write_text("a,b\n,2\n")
            (root / "a.csv").write_text("a,b\n1,2\n")
            files, _ = checker.collect_files([str(root)])
            self.assertEqual(files, [str(root / "a.csv")])

    def test_no_recursive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.csv").write_text("a,b\n1,2\n")
            (root / "sub").mkdir()
            (root / "sub" / "b.csv").write_text("a,b\n1,2\n")
            files, _ = checker.collect_files([str(root)], recursive=False)
            self.assertEqual(files, [str(root / "a.csv")])

    def test_exclude_pattern(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "draft-a.csv").write_text("a,b\n1,2\n")
            (root / "final.csv").write_text("a,b\n1,2\n")
            files, _ = checker.collect_files(
                [str(root)], exclude=["draft-*"])
            self.assertEqual(files, [str(root / "final.csv")])

    def test_direct_file_checked_despite_exclude_and_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "draft-data.txt"
            target.write_text("a,b\n,2\n")
            files, _ = checker.collect_files(
                [str(target)], exclude=["draft-*"])
            self.assertEqual(files, [str(target)])

    def test_missing_path_reported(self):
        files, missing = checker.collect_files(["/no-such-path-xyz"])
        self.assertEqual(files, [])
        self.assertEqual(missing, ["/no-such-path-xyz"])

    def test_uppercase_extension_walked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "UP.CSV").write_text("a,b\n1,2\n")
            files, _ = checker.collect_files([str(root)])
            self.assertEqual(files, [str(root / "UP.CSV")])

    def test_results_sorted_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "b.csv").write_text("a,b\n1,2\n")
            (root / "a.csv").write_text("a,b\n1,2\n")
            files, _ = checker.collect_files(
                [str(root / "b.csv"), str(root), str(root / "a.csv")])
            self.assertEqual(files, [str(root / "a.csv"),
                                     str(root / "b.csv")])


class TestCLI(unittest.TestCase):
    def run_cli(self, *args, stdin=None):
        return subprocess.run(
            [sys.executable, str(SRC), *args],
            input=stdin, capture_output=True, text=True, cwd=ROOT,
        )

    def test_clean_file_exit_0(self):
        result = self.run_cli("examples/good.csv")
        self.assertEqual(result.returncode, 0)
        self.assertIn("examples/good.csv: OK", result.stdout)
        self.assertIn("no empty rows or cells", result.stdout)

    def test_bad_file_exit_1(self):
        result = self.run_cli("examples/empty-cells.csv")
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL examples/empty-cells.csv:3:", result.stdout)

    def test_folder_exit_1_and_summary(self):
        result = self.run_cli("examples/")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Checked 5 file(s), 6 problem(s) in 3 file(s).",
                      result.stdout)

    def test_no_args_exit_2(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)

    def test_missing_path_exit_2(self):
        result = self.run_cli("no-such-file.csv")
        self.assertEqual(result.returncode, 2)
        self.assertIn("no such file or folder", result.stderr)

    def test_empty_folder_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli(tmp)
        self.assertEqual(result.returncode, 2)
        self.assertIn("no CSV files found", result.stderr)

    def test_bad_delimiter_exit_2(self):
        result = self.run_cli("--delimiter", ";;",
                              "examples/good.csv")
        self.assertEqual(result.returncode, 2)

    def test_bad_flag_exit_2(self):
        result = self.run_cli("--nope", "examples/good.csv")
        self.assertEqual(result.returncode, 2)

    def test_delimiter_flag(self):
        result = self.run_cli("--delimiter", ";",
                              "examples/semicolon.csv")
        self.assertEqual(result.returncode, 1)
        self.assertIn("empty cell in column 2", result.stdout)

    def test_stdin(self):
        result = self.run_cli("--stdin", stdin="a,b\n,2\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL <stdin>:2: empty cell in column 1",
                      result.stdout)

    def test_stdin_clean(self):
        result = self.run_cli("--stdin", stdin="a,b\n1,2\n")
        self.assertEqual(result.returncode, 0)

    def test_stdin_with_path_exit_2(self):
        result = self.run_cli("--stdin", "examples/good.csv")
        self.assertEqual(result.returncode, 2)

    def test_json_output(self):
        result = self.run_cli("--json", "examples/empty-cells.csv")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["problems"], 3)
        self.assertEqual(payload["summary"]["checked"], 1)
        self.assertEqual(payload["files"][0]["file"],
                         "examples/empty-cells.csv")
        self.assertEqual(payload["files"][0]["problems"][0]["line"], 3)
        self.assertIn("Checked 1 file(s), 3 problem(s)",
                      result.stderr)

    def test_json_clean(self):
        result = self.run_cli("--json", "examples/good.csv")
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["problems"], 0)

    def test_version(self):
        result = self.run_cli("--version")
        self.assertEqual(result.returncode, 0)
        self.assertIn("1.0.0", result.stdout)

    def test_exclude_flag(self):
        result = self.run_cli("--exclude", "empty-*.csv", "examples/")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("empty-cells", result.stdout)
        self.assertIn("header-gap", result.stdout)


class TestExamples(unittest.TestCase):
    def test_bundled_files_expected_problems(self):
        expected = {
            "good.csv": [],
            "empty-cells.csv": [
                (3, "empty cell in column 2"),
                (4, "empty cell in column 3"),
                (5, "empty cell in column 2"),
            ],
            "empty-rows.csv": [
                (3, "empty row (no cells)"),
                (5, "empty row (every cell is empty)"),
            ],
            "header-gap.csv": [(1, "empty cell in column 2")],
        }
        for name, want in expected.items():
            text = (EXAMPLES / name).read_text()
            got = [(p.line, p.reason)
                   for p in checker.check_text(text, name)]
            self.assertEqual(got, want, name)

    def test_semicolon_file_with_delimiter(self):
        text = (EXAMPLES / "semicolon.csv").read_text()
        got = [(p.line, p.reason)
               for p in checker.check_text(text, "semicolon.csv",
                                           delimiter=";")]
        self.assertEqual(got, [(3, "empty cell in column 2")])

    def test_sample_output_matches_fresh_run(self):
        result = subprocess.run(
            ["sh", "examples/run-example.sh"],
            capture_output=True, text=True, cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0)
        sample = (EXAMPLES / "sample-output.md").read_text()
        block = sample.split("```\n")[1]
        self.assertEqual(result.stdout, block)

    def test_readme_quoted_outputs_are_real(self):
        readme = README.read_text()
        for line in [
            "examples/good.csv: OK",
            "OK — 1 file(s) checked, no empty rows or cells.",
            "FAIL examples/empty-cells.csv:3: empty cell in column 2",
            "FAIL examples/empty-rows.csv:3: empty row (no cells)",
            "FAIL examples/empty-rows.csv:5: empty row (every cell is empty)",
            "FAIL examples/header-gap.csv:1: empty cell in column 2",
            "FAIL examples/semicolon.csv:3: empty cell in column 2",
            "Checked 5 file(s), 6 problem(s) in 3 file(s).",
            "FAIL <stdin>:3: empty row (no cells)",
        ]:
            self.assertIn(line, readme, line)


class TestHygiene(unittest.TestCase):
    def test_no_placeholder_text(self):
        banned = ["TODO", "FIXME", "XXX", "coming soon", "lorem"]
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if "tests" in path.parts:
                continue
            text = path.read_text(errors="replace")
            for word in banned:
                self.assertNotIn(word, text,
                                 f"{word} in {path.relative_to(ROOT)}")

    def test_no_absolute_paths(self):
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if "tests" in path.parts:
                continue
            text = path.read_text(errors="replace")
            self.assertNotIn("/home/hatch", text,
                             f"absolute path in {path.relative_to(ROOT)}")
            self.assertNotIn("/Users/", text,
                             f"absolute path in {path.relative_to(ROOT)}")
            self.assertNotIn("/tmp/", text,
                             f"absolute path in {path.relative_to(ROOT)}")

    def test_stdlib_only_imports(self):
        allowed_src = {
            "argparse", "csv", "fnmatch", "io", "json", "os", "sys",
            "pathlib",
        }
        allowed_tests = allowed_src | {
            "ast", "json", "subprocess", "tempfile", "unittest",
            "csv_empty_checker",
        }
        for path, allowed in [(SRC, allowed_src),
                              (Path(__file__), allowed_tests)]:
            tree = ast.parse(path.read_text())
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(a.name.split(".")[0]
                                    for a in node.names)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported.add(node.module.split(".")[0])
            self.assertTrue(imported <= allowed,
                            f"{path.name} imports non-stdlib: "
                            f"{imported - allowed}")
            self.assertNotIn("yaml", imported)

    def test_no_yaml_anywhere_in_source(self):
        text = SRC.read_text()
        self.assertNotIn("yaml", text)

    def test_no_secrets_in_repo(self):
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if "tests" in path.parts:
                continue
            text = path.read_text(errors="replace").lower()
            for marker in ["api_key", "api-key", "password =", "secret ="]:
                self.assertNotIn(marker, text,
                                 f"possible secret in {path.relative_to(ROOT)}")

    def test_gitignore_env_first(self):
        lines = (ROOT / ".gitignore").read_text().splitlines()
        self.assertEqual(lines[0], ".env")

    def test_ci_runs_this_test_file(self):
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
        self.assertIn("test_csv_empty_checker.py", ci)
        self.assertIn("push", ci)
        self.assertIn("pull_request", ci)


if __name__ == "__main__":
    unittest.main()
