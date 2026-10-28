# Case: `parameter-ports`

Inputs for `tests/test_parameter_ports.py`. The test is the oracle: it asserts
on the loaded model and the generated SSD and FMI structures, so this directory
holds no expected file.

## Artifacts

All paths are relative to this directory.

| Path | Kind |
| --- | --- |
| `template.sysml` | SysML v2 template, filled once per test |
| `connected-ports.sysml` | complete document: two parameter ports wired with `connect` |

`template.sysml` is filled per test by `render_fixture` with `$port`, `$markers`,
`$interface_decl`, `$interface_members`, and `$COMPOSITION_NAME`. It carries the
package scaffolding that would otherwise be repeated in every test body.

The short `port`, `markers`, `interface_decl`, and `interface_members`
fragments stay inline in the test on purpose: they are the case, not the
document.

## What this case proves

The set pins the parameter port contract: direction and marker validation,
rejection of the retired attribute carrier, flat FMI variables with `parameter`
causality, flat SSD connectors, and the refusal to `connect` two parameter
ports. The document is what a reviewer reads as SysML; the test decides pass or
fail.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-28 | Template and document moved out of the test module | Test bodies carried escaped document text |
