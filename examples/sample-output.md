# Sample output

Output of `sh examples/run-example.sh` — the checker run over the
whole `examples/` folder (5 files, 6 problems in 3 files):

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

`examples/semicolon.csv` passes here because it is checked with
the default comma delimiter — with commas, each line is a single
field with no empty cells. Run it with `--delimiter ';'` to check
it properly (see the README).
