# Case: `quoted-names`

Input documents for SysML v2 quoted declared names.

## Artifacts

| Path | Kind |
| --- | --- |
| `names.sysml` | Input |
| `bind.sysml` | Input |
| `composition.sysml` | Input |

No expected artifact: the tests assert the captured names, the exported text,
and the SSD connector summary.

## What this case proves

A SysML name is either a simple identifier or a single-quoted name. SSP/FMI
names can carry characters a SysML identifier cannot (dots, brackets, spaces,
leading digits), so the adapter stores the declared name without its quotes and
the exporter re-quotes it.

`names.sysml` declares a port attribute `'X[1]'`, a quoted SysML keyword
`'part'`, and a part definition named `'System.Top'`. The loader test proves the
names arrive as `X[1]`, `part`, and `System.Top`, and that the exporter re-emits
them quoted so the document reloads unchanged.

`bind.sysml` is a parameter-shaped document: a parameter interface member
`'pipeA.L'` is bound through a feature chain whose last segment is quoted. The
loader test proves the binding keeps `pipeA.L` as one segment rather than
splitting it on the dot.

`composition.sysml` connects two components over a port whose attributes include
`'X[1]'` and `'X[2]'`. The SSD test proves the generated connectors are
`feed.X[1]` and `feed.X[2]`, not `feed.'X[1]'`.

- **Conversion:** SysML v2 text → `Architecture` through
  `pyssp_sysml2.model.load`, back to text through
  `Architecture.export_declared`, and to SSD through `generate_ssd`.
- **Requirement / fault:** a quoted name must reach the artifact with its
  characters intact; a generator must never emit the quotes into an SSD name.
- **Level:** unit.
- **Input:** the three documents above, authored here for these tests.
- **Expected:** none. Each test asserts the captured fields, exported text, or
  SSD summary inline.
- **Independent oracle:** the tests.
- **Comparison:** exact tuples, strings, and summary lines.
- **Normalization:** `write_model` strips the file and keeps one trailing
  newline.
- **Volatile fields:** none.
- **Update policy:** edit the documents only together with the quoted-name tests
  in `tests/test_sysml_model.py` and `tests/test_generate_ssd.py`.
- **Notes:** the quoted names are deliberately minimal; the case covers name
  transport, not a specific FMU interface.

## Why a file

The quoted-name syntax is the contract under test; a reviewer has to read the
quotes as authored. Inlining it would hide the exact shape the parser and
exporter must preserve.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-11-03 | Created | Support SSP connector and parameter names that are not SysML identifiers. |
