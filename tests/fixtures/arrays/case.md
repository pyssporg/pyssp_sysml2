# Case: `arrays`

Input documents for fixed-multiplicity port usages.

## Artifacts

| Path | Kind |
| --- | --- |
| `ports.sysml` | Input |
| `mismatch.sysml` | Input (multiplicity mismatch must be refused) |

No expected artifact: the tests assert the captured multiplicity, the exported
text, the SSD connector/connection summary, and the raised error.

## What this case proves

A port usage may declare a fixed multiplicity (`port 'feed.X' : RealSignal[3]`).
The adapter stores the declared range, the exporter re-emits it, and
`generate ssd` expands one port into indexed connectors and one connection into
one connection per index.

Signal arrays are indexed from 1 to match FMI array variable names
(`feed.X[1]`, `feed.X[2]`, `feed.X[3]`). This differs from parameter lists,
which keep the 0-based SSV convention.

`mismatch.sysml` joins a 3-element port to a 2-element port; generation refuses
the connection instead of silently truncating.

- **Conversion:** SysML v2 text → `Architecture`, back to text, and to SSD.
- **Requirement / fault:** a fixed multiplicity must survive as an array, and a
  connection must not join arrays of different length.
- **Level:** unit.
- **Input:** the two documents above, authored here for these tests.
- **Expected:** none. The tests assert the model field, exported text, SSD
  summary, and error message inline.
- **Independent oracle:** the tests.
- **Comparison:** exact tuples, strings, and summary lines.
- **Normalization:** `write_model` strips the file and keeps one trailing
  newline.
- **Volatile fields:** none.
- **Update policy:** edit the documents only together with the array tests in
  `tests/test_sysml_model.py` and `tests/test_generate_ssd.py`.
- **Notes:** the flat port keeps the quoted name `feed.X`, so the indexed
  connector is `feed.X[1]` and not `feed[1].X`.

## Why a file

The array syntax and the mismatch are the contract under test; a reviewer has
to read the multiplicity as authored.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-11-03 | Created | Align signal arrays with SysML fixed multiplicity. |
