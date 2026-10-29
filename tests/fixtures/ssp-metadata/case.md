# Case: `ssp-metadata`

The SysML input for typed SSP metadata handed to an analysis.

## Artifacts

| Path | Kind |
| --- | --- |
| `architecture.sysml` | Input, `.replace()`d by two tests |

No expected artifact: the tests read the analysis descriptor JSON or the raised
error.

## What this case proves

The model declares an `SspMetadata` schema, a `LegacySsp` concrete definition
with `source = "models/ssp/example/ssp"`, and an analysis over it, so it proves an
analysis records the external model source and refuses to export it as an SSP or
SSD. One `.replace()` deletes the `source` attribute to prove the descriptor
then omits `model_source`; the other rewrites `LegacyBody :> SspModel` as
`PlainPart` to prove the role marker is required.

Origin: module-level literal in `tests/test_ssp_metadata.py`, written verbatim,
so the fixture bytes are the literal bytes. The replace calls are the case.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-28 | Moved out of `tests/test_ssp_metadata.py` | Document belongs in a file; derived variants stay `.replace()` edits |
