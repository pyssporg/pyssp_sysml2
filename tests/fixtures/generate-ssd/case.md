# Case: `generate-ssd`

The SysML inputs for SSD generation.

## Artifacts

| Path | Kind |
| --- | --- |
| `ports.sysml` | Input |
| `parts.sysml` | Input |
| `composition.sysml` | Input, template with `$COMPOSITION_NAME` |
| `core-metadata.sysml` | Input, template with `$COMPOSITION_NAME` |
| `retired-parameter-set.sysml` | Input, template with `$COMPOSITION_NAME` |
| `boundary.sysml` | Input, template with `$COMPOSITION_NAME` |
| `boundary-wrong-direction.sysml` | Input, template with `$COMPOSITION_NAME` |
| `boundary-to-boundary.sysml` | Input, template with `$COMPOSITION_NAME` |

No expected artifact: the SSD tests assert an SSD connector/connection summary,
top-level metadata, or the raised error.

## What this case proves

`ports.sysml` + `parts.sysml` + `composition.sysml` are the three-file split of
one architecture, proving cross-file resolution, array parameters, and
connection expansion into per-scalar SSD connections. `core-metadata.sysml` pins
the SSD version, name, default experiment, and empty component source.
`retired-parameter-set.sysml` pins the rejection of `pyssp_parameter_set`.
`boundary.sysml` proves a subpart-to-boundary wiring becomes an SSD connection
with a missing element end, including the inner system. The two boundary error
documents prove a boundary port used as a connection start and a
boundary-to-boundary connection are rejected.

Origin: inline literals (one `.format()` template) in
`tests/test_generate_ssd.py`; `BOUNDARY_MODEL` became `boundary.sysml` and the
format call became `render_fixture`. The composition name is a slot.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-28 | Moved out of `tests/test_generate_ssd.py` | Documents belong in files; rendered bytes unchanged |
