# Case: `cli`

The SysML inputs the command-line tests drive `pyssp` with.

## Artifacts

| Path | Kind |
| --- | --- |
| `architecture.sysml` | Input, template with `$COMPOSITION_NAME` |
| `parameter-architecture.sysml` | Input, template with `$COMPOSITION_NAME` |

Neither file is an expected artifact: each is written to `tmp_path` and the
generated SSD/SSV/SSM/SSP is what the test inspects.

## What this case proves

`architecture.sysml` is the smallest composition with a signal port, a source,
and a sink, wired once. Driving the CLI over it proves `generate ssd`,
`generate ssp` (design mode, no FMU), `sync ssd`, and the unknown-composition and
missing-SSD error paths operate on a real architecture directory.
`parameter-architecture.sysml` adds a parameter interface, a parameter set, and a
member bind; it proves `generate ssv`, `generate ssm`, the parameter-set prefix
option, and the parameter binding in the SSD.

Origin: inline f-strings in `write_cli_architecture` and
`write_parameter_cli_architecture` in `tests/test_cli.py`. The composition name
is the only varying part and is a slot, so the files are documents rather than
Python templates.

There are no fragments: the documents are complete.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-28 | Moved out of `tests/test_cli.py` | Documents belong in files; rendered bytes unchanged |
