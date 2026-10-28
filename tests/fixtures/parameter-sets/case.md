# Case: `parameter-sets`

Inputs for `tests/test_parameter_sets.py`. The test is the oracle: it asserts on
the generated SSV, SSM, SSD, and FMI structures, so this directory holds no
expected file.

## Artifacts

All paths are relative to this directory.

| Path | Kind |
| --- | --- |
| `template.sysml` | SysML v2 template, filled once per test |
| `two-sets-one-member.sysml` | complete document: two sets bound to one member |
| `two-disjoint-sets.sysml` | complete document: two sets bound to different members; used by the SSD and SSM tests |
| `interface-only.sysml` | complete document: interface without an applied set |

`template.sysml` is filled per test by `render_fixture` with
`$interface_marker`, `$interface_members`, `$sets`, `$composition`, and
`$COMPOSITION_NAME`. It carries the package scaffolding that would otherwise be
repeated in every test body.

The short `sets`, `composition`, and `interface_members` fragments stay inline
in the test on purpose: they are the case, not the document.

## What this case proves

The set pins the documented parameter dialect: marker definitions, parameter
ports, applied and unapplied sets, per-member and whole-object binds, and the
SSV/SSM/SSD/FMI artifacts generated from them. A deleted document removes the
only place a change to that dialect is reviewed as SysML.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-28 | Documents moved out of the test module | Every test body started with an escaped document |
