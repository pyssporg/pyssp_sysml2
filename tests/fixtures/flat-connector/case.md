# Case: `flat-connector`

The SysML inputs for the `pyssp_flat_connector` control attribute.

## Artifacts

| Path | Kind |
| --- | --- |
| `ports.sysml` | Input, template with `$flat_connector` |
| `parts.sysml` | Input |
| `composition.sysml` | Input, template with `$COMPOSITION_NAME` |

No expected artifact: the test generates an SSD into `tmp_path` and asserts its
connector names and connection endpoints.

## What this case proves

`ports.sysml` declares a signal port with one member, `x`. The one port
definition is rendered with no attribute, with
`pyssp_flat_connector = false`, and with `pyssp_flat_connector = true`; the
`false` and absent forms must produce per-member connectors (`sig.x`) and the
`true` form a single flattened connector (`sig`). Reading the attribute's
presence instead of its value would make `false` flatten, which this case
detects. `parts.sysml` and `composition.sysml` provide the two components and
one connection so the SSD connection endpoints can be compared with the
connector names.

Origin: the release's single intended behaviour change; the documents are new,
authored for this case.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-11-05 | Case added | Pin `pyssp_flat_connector = false` as per-member, not flat |
