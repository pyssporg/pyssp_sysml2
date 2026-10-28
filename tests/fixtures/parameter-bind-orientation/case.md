# Case: `parameter-bind-orientation`

Inputs for `tests/test_parameter_bind_orientation.py`. The test is the oracle:
it asserts on the resolved binding and on generator errors, so this directory
holds no expected file.

## Artifacts

All paths are relative to this directory.

| Path | Kind |
| --- | --- |
| `template.sysml` | SysML v2 template, filled once per test |

`template.sysml` is filled per test by `render_fixture` with `$parts`,
`$bind_line`, and `$COMPOSITION_NAME`. It carries the package scaffolding that
would otherwise be repeated in every test body.

The short `parts` and `bind_line` fragments stay inline in the test on purpose:
they are the case, not the document.

## What this case proves

The set pins the canonical parameter bind orientation: the parameter port is on
the left and the set usage on the right. It distinguishes member binds from
whole-object binds, rejects the reversed form with a rewrite hint, rejects
port-to-port binds, and ignores binds that do not touch a parameter port.
Generators enforce the same rule, not just the resolver.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-28 | Template moved out of the test module | Test bodies carried escaped document text |
