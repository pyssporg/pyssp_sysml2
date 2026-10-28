# Case: `generate-model-descriptions`

The SysML inputs for FMI model-description generation.

## Artifacts

| Path | Kind |
| --- | --- |
| `status-component.sysml` | Input, template with `$COMPOSITION_NAME` |
| `ports.sysml` | Input |
| `parts.sysml` | Input, template with `$COMPOSITION_NAME` |
| `flat-parameters.sysml` | Input, template with `$COMPOSITION_NAME` |
| `two-components.sysml` | Input, template with `$COMPOSITION_NAME` |

No expected artifact is committed: the tests parse the generated
`modelDescription.xml` and assert a variable/structural summary, the root
metadata, the pinned guid, or the raised error.

## What this case proves

`status-component.sysml` is the single-output composition used by the
determinism, clock, guid, and checkout-purity tests; it is used twice because one
test names it directly and the others go through `_write_status_component`.
`ports.sysml` and `parts.sysml` are written as two files of one architecture,
which proves a port definition may live in a different file from the part using
it, with array parameters typed `Integer[2]` and `Boolean[2]`.
`flat-parameters.sysml` pins the rejection of a bare parameter attribute.
`two-components.sysml` proves one output document per referenced component type.

Origin: inline literals in `tests/test_generate_model_descriptions.py`; the
f-strings differed only in the composition name, which is now a slot.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-28 | Moved out of `tests/test_generate_model_descriptions.py` | The document duplicated by `_write_status_component` is now one file, not two copies |
