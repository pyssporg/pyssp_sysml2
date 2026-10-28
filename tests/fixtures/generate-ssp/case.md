# Case: `generate-ssp`

The SysML inputs and the mismatched FMI document for SSP packaging.

## Artifacts

| Path | Kind |
| --- | --- |
| `template.sysml` | Input, template with `$parameter_defs`, `$metadata_fields`, `$flat_connector`, `$parameter_port`, `$composition_parameters`, `$COMPOSITION_NAME` |
| `nested-component.sysml` | Input, template with `$leaf_fmu`, `$COMPOSITION_NAME` |
| `mismatched-model-description.xml` | Input, FMI 2.0 model description zipped as a fake FMU |

No expected artifact: packaged SSPs are opened through `pyssp_standard` and
asserted by member names and component fields.

## What this case proves

`template.sysml` is the one architecture `_write_architecture` varies. The
parameter block, the metadata fields, the parameter port, the composition
bindings, and the flat-connector attribute are computed in Python and passed as
slots, because whether they are present is the case: parameterized versus not,
source present, missing, or absent, CoSimulation versus ModelExchange. The
conditional that builds the block stays in Python; the document no longer does.
`nested-component.sysml` proves a part inside a subpart is packaged and
validated, with the FMU path a slot. `mismatched-model-description.xml` declares
a variable `other` where the SSD expects `output`, so it proves connector-name
validation fails and that skipping validation packages it anyway.

Origin: inline f-string in `_write_architecture`, an f-string in the
nested-component test, and an XML literal in `_write_mismatched_fmu`, all in
`tests/test_generate_ssp.py`.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-28 | Moved out of `tests/test_generate_ssp.py` | Documents belong in files; the Python conditional stays, the document does not |
