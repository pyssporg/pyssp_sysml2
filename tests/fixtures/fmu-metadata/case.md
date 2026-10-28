# Case: `fmu-metadata`

The SysML inputs for typed FMU metadata: schema, concrete definition, and the
part that uses it.

## Artifacts

| Path | Kind |
| --- | --- |
| `template.sysml` | Input, template with `$marker`, `$concrete`, `$part_body`, `$COMPOSITION_NAME` |
| `parameter-connector.sysml` | Input, template with `$COMPOSITION_NAME` |
| `retired-implementation.sysml` | Input, template with `$COMPOSITION_NAME` |

None is an expected artifact; assertions read the loaded model, the generated
SSD, or the raised error.

## What this case proves

`template.sysml` is the one composition every metadata test varies. The marker
(the schema part definition), the concrete definition, and the part body are the
only parts that change, and they stay inline in `_metadata_model` on purpose:
they are short fragments (under the 15-line document limit) whose point is the
difference between two tests, not a document a reviewer reads on its own.
Filling the template proves default resolution, value-less redeclaration, a
missing marker, an unknown member, a non-string value, duplicate metadata, a
schema used directly, unmarked usage, and metadata on a system being rejected.
`parameter-connector.sysml` proves metadata is not emitted as a parameter
connector even when a parameter port is present.
`retired-implementation.sysml` pins the rejection of the retired
`pyssp_implementation` attribute.

Origin: inline f-strings in `tests/test_fmu_metadata.py` (the `_metadata_model`
template and two complete documents). The template is filled with
`string.Template`, so SysML braces are literal.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-28 | Moved out of `tests/test_fmu_metadata.py` | The documents belong in files; marker, concrete, and part body stay inline as fragments |
